import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { surface, compareSurface } from './frame_capture.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const russian = JSON.parse(
  await readFile(root + 'frontend/src/locales/ru.json', 'utf8')
);
const translate = (text, language) =>
  language === 'ru' ? russian[text] || text : text;
const out =
  root +
  (process.env.MESSAGES_FRAME_OUTPUT || 'tools/frame_messages/output') +
  '/';
const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
const digest = async (path) =>
  createHash('sha256')
    .update(await readFile(path))
    .digest('hex');
async function fresh() {
  for (const [prefix, files] of [
    [root + 'src/tactic_stream/shared_ui/', native.shared],
    ['D:/code/th_codex/', native.nativeSources],
    [root, native.driverSources]
  ])
    for (const [name, hash] of Object.entries(files))
      assert.equal(
        await digest(prefix + name),
        hash,
        'Stale messages source ' + name
      );
}
async function fingerprints() {
  const sources = {};
  for (const name of await readdir(root + 'frontend/src', { recursive: true }))
    if (/\.(vue|css|js|mjs|json)$/.test(name))
      sources['frontend/src/' + name.replaceAll('\\', '/')] = await digest(
        root + 'frontend/src/' + name
      );
  for (const name of [
    'frontend/tests/frame_messages.mjs',
    'frontend/tests/frame_capture.mjs',
    ...(await readdir(root + 'tools/frame_messages'))
      .filter((name) => /\.(vue|html|mjs|py)$/.test(name))
      .map((name) => 'tools/frame_messages/' + name)
  ])
    sources[name] = await digest(root + name);
  return sources;
}
await fresh();
const browserSources = await fingerprints();
let server, browser;
const errors = [],
  captures = [];
try {
  server = await createServer({
    root,
    configFile: false,
    plugins: [vue()],
    publicDir: root + 'frontend/public',
    resolve: {
      alias: {
        vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
      }
    },
    logLevel: 'error',
    server: { host: '127.0.0.1', port: 0, watch: null }
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: native.scale || 1
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.clock.install({ time: new Date('2026-10-18T09:59:55Z') });
  let current;
  await page.route('**/admin/**', async (route) => {
    const action = route.request().url().split('/').at(-1);
    let result = {};
    if (action === 'list')
      result = {
        initialized: true,
        canCreateGroup: true,
        canDeleteMessages: true,
        permissions: Object.fromEntries(
          [
            'create',
            'send',
            'upload',
            'rename',
            'members',
            'clear',
            'delete',
            'edit',
            'forward',
            'pin',
            'reaction',
            'delete-message'
          ].map((key) => [key, true])
        ),
        conversations: current.model.conversations
      };
    if (action === 'activity-feed')
      result = {
        records: current.model.activity,
        users: current.model.users,
        nextOffset: 1,
        hasMore: false,
        total: 1,
        dayCounts: [],
        counts: {}
      };
    if (action === 'people') result = { users: current.model.users };
    if (action === 'history')
      result = {
        messages: current.model.messages,
        pinHistory: current.model.pinHistory || []
      };
    await route.fulfill({ json: { result } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_messages/');
  await page.waitForFunction(() => !!window.messagesFixture);
  for (const record of native.captures.filter((row) => !row.original)) {
    await page.clock.setSystemTime(new Date('2026-10-18T09:59:55Z'));
    await page.setViewportSize(
      [
        'forwarding',
        'view-members',
        'history',
        'pin-history',
        'files'
      ].includes(record.fixture.screen)
        ? { width: 1000, height: 620 }
        : { width: 1600, height: 1000 }
    );
    current = record.fixture;
    await page.evaluate(
      (fixture) => window.messagesFixture.show(fixture),
      record.fixture
    );
    await page.evaluate(() => document.activeElement?.blur());
    await page.mouse.move(1590, 990);
    if (record.fixture.screen === 'forwarding') {
      const row = page
        .locator('.messages-viewport[data-current=true] .message-row')
        .last();
      await row.locator('[data-frame=messageActionsButton]').click();
      await page
        .locator('.message-actions')
        .getByRole('button', {
          name: translate('Forward', record.fixture.language),
          exact: true
        })
        .click();
      for (let i = 0; i < 5; i++)
        await page.evaluate(() => new Promise(requestAnimationFrame));
    }
    const panel = ['view-members', 'history', 'pin-history', 'files'].includes(
      record.fixture.screen
    );
    if (panel) {
      if (record.fixture.screen === 'history') {
        const row = page
          .locator('.messages-viewport[data-current=true] .message-row')
          .last();
        await row.locator('[data-frame=messageActionsButton]').click();
        await page
          .locator('.message-actions')
          .getByRole('button', {
            name: translate('Edit history', record.fixture.language),
            exact: true
          })
          .click();
      } else if (record.fixture.screen === 'view-members')
        await page.locator('[data-frame=chatMembers]').click();
      else if (record.fixture.screen === 'files')
        await page.locator('[data-frame=chatFiles]').click();
      else {
        await page.locator('[data-frame=chatActionsButton]').click();
        await page
          .locator('.chat-actions')
          .getByRole('button', {
            name: translate('Pin history', record.fixture.language),
            exact: true
          })
          .click();
      }
      await page
        .locator('.messages-popup>.account-panel:popover-open')
        .waitFor();
    }
    const full = ['messages', 'activity', 'notifications'].includes(
      record.fixture.screen
    );
    const selector = full
      ? {
          messages: '.messages-dialog',
          activity: '.activity-dialog:not(.system-activity-dialog)',
          notifications: '.system-activity-dialog'
        }[record.fixture.screen]
      : panel
        ? '.messages-popup>.account-panel:popover-open'
        : record.fixture.screen === 'forwarding'
          ? '.messages-forward-surface'
          : '#messages-fixture';
    const expected = {
      ...record,
      frameIds: record.frameIds.filter((id) => !id.startsWith('materialIcon'))
    };
    if (record.fixture.screen === 'messages')
      expected.frameIds.push(
        'messageComposerEmojiButton',
        'messageComposerSendButton'
      );
    const image = record.image.replace('-native-', '-stream-');
    if (full) {
      const box = await page.locator(selector).boundingBox();
      await page.screenshot({
        path: out + image,
        clip: {
          x: box.x + 1,
          y: box.y + 41,
          width: record.fixture.width,
          height: record.fixture.height
        },
        animations: 'disabled'
      });
    } else if (panel) {
      const box = await page.locator(selector).boundingBox();
      await page.screenshot({
        path: out + image,
        clip: {
          x: box.x + 14,
          y: box.y + 14,
          width: record.fixture.width,
          height: record.fixture.height
        },
        animations: 'disabled'
      });
    } else
      await page
        .locator(selector)
        .screenshot({ path: out + image, animations: 'disabled' });
    const actual = await surface(page, selector);
    if (panel) {
      for (const box of Object.values(actual.boxes)) {
        box.x -= 14;
        box.y -= 14;
      }
      actual.origin.x += 14;
      actual.origin.y += 14;
    }
    if (full) {
      for (const boxes of [actual.boxes, actual.interiors])
        for (const box of Object.values(boxes)) {
          box.x -= 1;
          box.y -= 41;
        }
    }
    await writeFile(
      out + 'last-pair.json',
      JSON.stringify(
        {
          actual,
          expected,
          ports: await page
            .locator(selector)
            .locator('.activity-sentence-port')
            .evaluateAll((ns) =>
              ns.map((n) => ({
                html: n.innerHTML,
                font: getComputedStyle(n).font
              }))
            )
        },
        null,
        2
      )
    );
    const checked = await compareSurface(
      page,
      selector,
      actual,
      expected,
      record.image
    );
    captures.push({ image, fixture: record.fixture, ...checked });
    console.log('Compared', image, checked.rectangles);
  }
  assert.deepEqual(errors, []);
  await fresh();
  assert.deepEqual(
    await fingerprints(),
    browserSources,
    'Sources changed during browser captures'
  );
  await writeFile(
    out + 'browser.json',
    JSON.stringify({ status: 'passed', captures, browserSources }, null, 2)
  );
  console.log('PASS production messages pairs:', captures.length);
} finally {
  if (browser) await browser.close();
  if (server) await server.close();
}
