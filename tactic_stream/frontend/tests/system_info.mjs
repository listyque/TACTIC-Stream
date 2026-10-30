import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import {
  describe,
  report
} from '../../src/tactic_stream/shared_ui/features/support/diagnostics/system.ui.mjs';

const facts = {
  cpuCount: 2,
  mailConfigured: true,
  mailFrom: 'fixture@example.invalid',
  links: [
    { name: 'shots', title: 'Shots', url: '/projects/one/?system_link=shots' }
  ],
  internalLinks: [
    { name: 'shots', title: 'Shots', url: '/projects/one/?system_link=shots' },
    { name: 'users', title: 'Users', url: '/projects/one/?system_link=users' }
  ],
  sections: [
    {
      title: 'Server',
      fields: [
        ['OS', 'Fixture OS'],
        ['Node Name', 'fixture']
      ]
    },
    {
      title: 'Asset Folders',
      fields: [
        ['default', '/fixture/' + 'long-path/'.repeat(20)],
        ['Writable (access check)', false]
      ]
    }
  ]
};
for (const language of ['en', 'ru'])
  for (const width of [320, 800]) {
    const nodes = describe(facts, width, 600, language).nodes;
    assert.ok(nodes.every((n) => n.x >= 0 && n.x + n.width <= width));
    assert.ok(report(facts, language).includes('Fixture OS'));
  }
assert.ok(report(facts, 'ru').includes('Нет'));
const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  publicDir: root + 'frontend/public',
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: { host: '127.0.0.1', port: 0, watch: null },
  logLevel: 'error'
});
let browser;
try {
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars'],
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    deviceScaleFactor: Number(process.env.FRAME_CAPTURE_DPR || 1.5),
    viewport: { width: 1000, height: 780 },
    permissions: ['clipboard-read', 'clipboard-write']
  });
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  const captures = [],
    output = process.env.SYSTEM_INFO_OUTPUT;
  if (output) await mkdir(output, { recursive: true });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  let reads = 0,
    fail = false,
    hold;
  const actions = [];
  await page.addInitScript(() => {
    window.openedPages = [];
    window.open = (value) => {
      window.openedPages.push(value);
      return { opener: null };
    };
  });
  await page.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    if (payload.method === 'log')
      return route.fulfill({
        contentType: 'application/json',
        body: '{"result":true}'
      });
    assert.equal(payload.method, 'execute_class_method');
    assert.equal(
      payload.args[1],
      'tactic.ui.app.system_info_wdg.SystemInfoWdg'
    );
    const method = payload.args[2];
    actions.push({ method, values: payload.args[3] });
    if (method !== 'get_info')
      return route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          result:
            method === 'connection_probe'
              ? { node: 'fixture', pid: 1, port: 8081 }
              : method === 'performance_probe'
                ? { rows: 1, columns: 2 }
                : { message: 'Script completed' }
        })
      });
    reads++;
    if (hold) {
      const pending = hold;
      hold = null;
      await pending;
    }
    await route.fulfill({
      status: fail ? 403 : 200,
      contentType: 'application/json',
      body: JSON.stringify(
        fail ? { error: 'Fixture disconnected' } : { result: facts }
      )
    });
  });
  await page.goto(
    server.resolvedUrls.local[0] + 'tools/frame_foundation/system-info.html'
  );
  await page.getByRole('button', { name: 'System Info', exact: true }).click();
  const dialog = page.locator('.system-info-dialog'),
    text = dialog.locator('[data-frame=systemValue_1]');
  await page.waitForFunction(() =>
    document
      .querySelector('[data-frame=systemValue_1]')
      ?.textContent.includes('Fixture OS')
  );
  assert.equal(reads, 1);
  for (const [width, language] of [
    [1000, 'en'],
    [344, 'ru']
  ]) {
    await page.setViewportSize({ width, height: 780 });
    await page.evaluate(
      (value) => window.systemInfoHarness.language(value),
      language
    );
    if (language === 'ru')
      await page
        .getByRole('dialog', { name: 'Информация о системе', exact: true })
        .waitFor();
    await dialog
      .getByRole('button', {
        name: language === 'ru' ? 'Копировать' : 'Copy',
        exact: true
      })
      .click();
    assert.ok(
      (await page.evaluate(() => navigator.clipboard.readText())).includes(
        'Fixture OS'
      )
    );
    const geometry = await dialog.evaluate((el) => ({
      width: el.clientWidth,
      scroll: el.scrollWidth
    }));
    assert.ok(geometry.scroll <= geometry.width + 1, JSON.stringify(geometry));
    assert.equal(
      await dialog.locator('textarea').count(),
      0,
      'No replacement report editor'
    );
    if (output) {
      const frame = dialog.locator('.system-info-body > .frame-view');
      const bounds = await frame.boundingBox();
      const client = await page.evaluate(() => ({
        title: 'Browser',
        fields: [
          ['User Agent', navigator.userAgent],
          ['Time zone', Intl.DateTimeFormat().resolvedOptions().timeZone]
        ]
      }));
      captures.push({
        width: bounds.width,
        height: bounds.height,
        language,
        model: {
          ...facts,
          sender: facts.mailFrom,
          recipients: facts.mailFrom,
          sections: [...facts.sections, client]
        },
        nodes: await frame
          .locator(
            '[data-frame=systemRefresh], [data-frame=systemCopy], [data-frame=systemBody]'
          )
          .evaluateAll((elements) =>
            elements.map((element) => ({
              id: element.dataset.frame,
              x: parseFloat(element.style.left),
              y: parseFloat(element.style.top),
              width: parseFloat(element.style.width),
              height: parseFloat(element.style.height)
            }))
          )
      });
      await frame.screenshot({ path: `${output}/${language}-browser.png` });
    }
    const refresh = dialog.getByRole('button', {
      name: language === 'ru' ? 'Обновить' : 'Refresh',
      exact: true
    });
    await refresh.focus();
    await page.keyboard.press('Space');
    await page.waitForFunction(
      () => !document.querySelector('[data-frame=systemRefresh]')?.disabled
    );
  }
  assert.equal(reads, 3);
  await dialog.locator('[data-frame=systemBalanceTest]').click();
  await dialog.locator('[data-frame=systemBalanceTestResult]').waitFor();
  assert.equal(
    actions.filter((row) => row.method === 'connection_probe').length,
    11
  );
  await dialog.locator('[data-frame=systemPerformanceTest]').click();
  await dialog.locator('[data-frame=systemPerformanceTestResult]').waitFor();
  assert.equal(
    actions.filter((row) => row.method === 'performance_probe').length,
    4
  );
  await dialog
    .locator('[data-frame=systemMailFrom]')
    .fill('from@example.invalid');
  await dialog.locator('[data-frame=systemMailTo]').fill('to@example.invalid');
  await dialog.locator('[data-frame=systemEmailTest]').click();
  await dialog.locator('[data-frame=systemEmailTestResult]').waitFor();
  assert.deepEqual(
    actions.find((row) => row.values?.action === 'email').values,
    {
      action: 'email',
      values: {
        sender: 'from@example.invalid',
        recipients: 'to@example.invalid'
      }
    }
  );
  await dialog.locator('[data-frame=systemHandoffTest]').click();
  await dialog.locator('[data-frame=systemHandoffTestResult]').waitFor();
  assert.ok(
    (
      await dialog.locator('[data-frame=systemHandoffTestResult]').innerText()
    ).includes('ТХ')
  );
  await dialog.locator('[data-frame=systemIncludeInternal]').click();
  await dialog.locator('[data-frame=systemLinkTest]').click();
  assert.equal((await page.evaluate(() => window.openedPages)).length, 2);
  await dialog.locator('[data-frame=systemOpenLink_0]').click();
  assert.equal((await page.evaluate(() => window.openedPages)).length, 3);
  await dialog.locator('[data-frame=systemScriptPath]').fill('tests/probe');
  await dialog.locator('[data-frame=systemScriptTest]').click();
  await dialog.locator('[data-frame=systemScriptTestResult]').waitFor();
  assert.deepEqual(
    actions.find((row) => row.values?.action === 'script').values,
    { action: 'script', values: { path: 'tests/probe' } }
  );
  await dialog.locator('[data-frame=systemClearSidebar]').click();
  await dialog.locator('[data-frame=systemClearSidebarResult]').waitFor();
  assert.ok(actions.some((row) => row.values?.action === 'clear_sidebar'));
  if (output)
    await dialog.screenshot({ path: output + '/actions-browser.png' });
  fail = true;
  await dialog.locator('[data-frame=systemRefresh]').click();
  await dialog.getByText('Fixture disconnected', { exact: true }).waitFor();
  assert.ok(await dialog.locator('[data-frame=systemCopy]').isDisabled());
  await page.keyboard.press('Escape');
  await page.waitForFunction(
    () => !document.querySelector('.system-info-dialog')?.open
  );
  fail = false;
  let release;
  hold = new Promise((resolve) => {
    release = resolve;
  });
  await page.locator('#app > .app-button').click();
  await page.waitForFunction(
    () => document.querySelector('.system-info-dialog')?.open
  );
  await page.evaluate(() => window.systemInfoHarness.signOut());
  release();
  await page.waitForFunction(
    () => !document.querySelector('.system-info-dialog')?.open
  );
  assert.equal(await text.count(), 0);
  assert.deepEqual(errors, []);
  if (output)
    await writeFile(
      `${output}/geometry.json`,
      JSON.stringify(captures, null, 2)
    );
  console.log(
    'PASS System Info: real browser mouse/keyboard, EN/RU narrow/wide, copy, read-only, refresh, failure, close and sign-out stale response'
  );
} finally {
  await browser?.close();
  await server.close();
}
