import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium, firefox } from 'playwright';
import * as Cells from '../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';

for (const progress of [
  undefined,
  { state: 'unconfigured' },
  { state: 'unavailable' },
  { state: 'ready', complete: 0, total: 0 },
  { state: 'ready', complete: 1, total: 2 },
  { state: 'ready', complete: 2, total: 2 }
]) {
  for (const [width, height] of [
    [99, 36],
    [120, 58]
  ]) {
    const scene = Cells.processProgress({ progress }, width, height, 'en');
    validateScene(scene, {}, {});
    const children = scene.nodes[0].children;
    assert.equal(
      children.find((node) => node.id === 'processProgressCount').text,
      progress?.state === 'ready'
        ? progress.complete + '/' + progress.total
        : 'N/A'
    );
    assert.equal(
      children.some((node) => node.kind === 'Chart'),
      progress?.state === 'ready'
    );
  }
}

const root = fileURLToPath(new URL('../../', import.meta.url));
const records = [
  {
    process: 'assets',
    processLabel: 'ASSETS',
    processType: 'progress',
    processColor: '#78a6c4',
    progress: { state: 'ready', complete: 3, total: 10 }
  },
  {
    process: 'model',
    processLabel: 'Model',
    status: 'Review',
    statusColor: '#5caa70',
    assigned: 'anna',
    assignedIdentity: {
      displayName: 'Anna',
      initials: 'A',
      avatarColor: '#43796c'
    },
    bidStart: '2026-10-28',
    bidEnd: '2026-11-02',
    simpleDates: true
  },
  {
    process: 'rig',
    processLabel: 'Подготовка персонажа',
    status: 'На проверке',
    processColor: '#a48bd2'
  }
];
const server = await createServer({
  root,
  configFile: false,
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
  const native = process.env.STREAM_BROWSER_ENGINE === 'firefox';
  browser = await (native ? firefox : chromium).launch({
    headless: true,
    ...(native ? {} : { channel: 'msedge' })
  });
  const page = await browser.newPage({ viewport: { width: 416, height: 108 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/process-card-fixture', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><div id="app"></div>'
    })
  );
  await page.goto(server.resolvedUrls.local[0] + 'process-card-fixture');
  const entry = await server.transformRequest('/frontend/src/main.js');
  await page.evaluate(
    async ({ vueUrl, records }) => {
      const { createApp, h } = await import(vueUrl);
      const { default: TaskCards } = await import(
        '/frontend/src/features/interface/TaskCards.vue'
      );
      const { appearance, initializeAppearance } = await import(
        '/frontend/src/appearance.js'
      );
      await import('/frontend/src/theme.css');
      await import('/frontend/src/style.css');
      initializeAppearance();
      Object.assign(appearance, {
        theme: 'md3',
        mode: 'dark',
        language: 'en',
        hoverAnimations: false,
        clickAnimations: false
      });
      window.events = [];
      createApp({
        render: () =>
          h(
            'div',
            {
              style:
                'position:absolute;left:12px;top:12px;width:392px;height:84px'
            },
            [
              h(TaskCards, {
                tasks: records,
                editable: true,
                expanded: true,
                height: 84,
                onInspect: (task) =>
                  window.events.push(['inspect', task.process]),
                onEdit: (task, field) =>
                  window.events.push(['edit', task.process, field])
              })
            ]
          )
      }).mount('#app');
    },
    { vueUrl: entry.code.match(/from "([^"]+)"/)[1], records }
  );
  const cards = page.locator('.task-card');
  await cards.first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  const geometry = await cards.evaluateAll((cards) =>
    cards.map((card) => ({
      bounds: card.getBoundingClientRect().toJSON(),
      fields: [...card.querySelectorAll('.task-cell-display')].map((field) => {
        const label = field.querySelector(
          '[data-frame=taskTableCellDisplayLabel]'
        );
        return {
          x: label.getBoundingClientRect().x,
          weight: getComputedStyle(label).fontWeight,
          background: getComputedStyle(
            field.querySelector('[data-frame=taskTableCellSurface]')
          ).backgroundColor
        };
      })
    }))
  );
  for (const card of geometry) {
    assert.equal(card.bounds.width, 128);
    assert.equal(card.bounds.height, 84);
    assert.equal(card.fields[0]?.x, card.fields[1]?.x);
    assert(card.fields.every((field) => field.weight === '400'));
    assert(
      card.fields.every((field) => field.background === 'rgba(0, 0, 0, 0)')
    );
  }
  assert.equal(
    await cards
      .first()
      .getByRole('button', { name: 'Edit task status', exact: true })
      .count(),
    0
  );
  assert.equal(
    await cards
      .first()
      .locator('[data-frame=processProgressCount]')
      .innerText(),
    '3/10'
  );
  await cards
    .first()
    .getByRole('button', { name: 'Related tasks', exact: true })
    .click();
  await cards
    .nth(1)
    .getByRole('button', { name: 'Task Inspector', exact: true })
    .click();
  await cards
    .nth(1)
    .getByRole('button', { name: 'Edit task status', exact: true })
    .click();
  await cards
    .nth(1)
    .getByRole('button', { name: 'Edit task assignee', exact: true })
    .click();
  await cards
    .nth(1)
    .getByRole('button', { name: 'Edit task dates', exact: true })
    .click();
  assert.deepEqual(await page.evaluate(() => window.events), [
    ['inspect', 'assets'],
    ['inspect', 'model'],
    ['edit', 'model', 'status'],
    ['edit', 'model', 'assigned'],
    ['edit', 'model', 'bid_start_date']
  ]);
  await page.mouse.move(510, 120);
  if (process.env.PROCESS_CARD_CAPTURE) {
    await mkdir(process.env.PROCESS_CARD_CAPTURE, { recursive: true });
    await page.screenshot({
      path:
        process.env.PROCESS_CARD_CAPTURE +
        '/browser-' +
        (native ? 'firefox' : 'edge') +
        '.png'
    });
    await writeFile(
      process.env.PROCESS_CARD_CAPTURE + '/browser.json',
      JSON.stringify(geometry, null, 2)
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS process cards: flat aligned fields, readable progress state, no-date label, preserved size and all actions'
  );
} finally {
  await browser?.close();
  await server.close();
}
