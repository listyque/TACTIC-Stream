import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium, firefox } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'clipboard-fixture',
      configureServer(server) {
        server.middlewares.use((request, response, next) => {
          if (request.url !== '/clipboard-test.html') return next();
          response.setHeader('Content-Type', 'text/html');
          response.end('<!doctype html><div id="app"></div>');
        });
      }
    }
  ],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: null,
    allowedHosts: ['clipboard.test']
  },
  logLevel: 'error'
});
let browser;
try {
  await server.listen();
  const isFirefox = process.env.STREAM_BROWSER_ENGINE === 'firefox';
  browser = await (isFirefox ? firefox : chromium).launch({
    headless: !(isFirefox && process.env.CLIPBOARD_REAL_KEYBOARD),
    ...(isFirefox
      ? {
          firefoxUserPrefs: { 'network.dns.localDomains': 'clipboard.test' }
        }
      : {
          channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
          args: [
            '--host-resolver-rules=MAP clipboard.test 127.0.0.1',
            '--no-proxy-server'
          ]
        })
  });
  const page = await browser.newPage({
    viewport: { width: 1100, height: 800 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/**', async (route) => {
    const action = route.request().url().split('/').at(-1);
    let result = {};
    if (action === 'list')
      result = {
        initialized: true,
        permissions: { create: false, send: true, upload: true },
        conversations: [
          {
            conversationId: 'favorites',
            title: 'Favorites',
            isPersonalNotes: true,
            members: ['admin']
          }
        ]
      };
    if (action === 'people')
      result = {
        users: [{ login: 'admin', displayName: 'Admin', current: true }]
      };
    if (action === 'history') result = { messages: [], pinHistory: [] };
    if (action === 'rpc')
      result = { info: { current_user: 'admin', notes: [], identities: [] } };
    await route.fulfill({ json: { result } });
  });
  const local = server.resolvedUrls.local[0];
  if (process.env.CLIPBOARD_REAL_KEYBOARD) {
    if (!isFirefox)
      await page
        .context()
        .grantPermissions(['clipboard-read', 'clipboard-write'], {
          origin: local
        });
    await page.goto(local + 'clipboard-test.html');
    await page.evaluate(async () => {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 16;
      canvas.getContext('2d').fillRect(0, 0, 16, 16);
      const image = await new Promise((resolve) =>
        canvas.toBlob(resolve, 'image/png')
      );
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': image })
      ]);
    });
  }
  await page.goto(
    local.replace('127.0.0.1', 'clipboard.test') + 'clipboard-test.html'
  );
  assert.equal(
    await page.evaluate(() => isSecureContext),
    false,
    'Use a real HTTP non-localhost origin'
  );
  assert.equal(await page.evaluate(() => !!navigator.clipboard?.read), false);
  const entry = await server.transformRequest('/frontend/src/main.js');
  const vueUrl = entry.code.match(/from "([^"]+)"/)[1];
  await page.evaluate(async (vueUrl) => {
    const { createApp, h, ref, nextTick } = await import(vueUrl);
    const { default: Messages } = await import(
      '/frontend/src/features/messages/MessagesView.vue'
    );
    const { default: Notes } = await import(
      '/frontend/src/features/objects/NotesPanel.vue'
    );
    const { windowDirective } = await import(
      '/frontend/src/controls/window.js'
    );
    const { appearance, initializeAppearance } = await import(
      '/frontend/src/appearance.js'
    );
    await import('/frontend/src/theme.css');
    await import('/frontend/src/style.css');
    initializeAppearance();
    Object.assign(appearance, {
      language: 'en',
      mode: 'dark',
      theme: 'md3',
      clickAnimations: false,
      hoverAnimations: false
    });
    const messages = ref(null),
      notes = ref(null);
    createApp({
      render: () => [
        h(Messages, {
          ref: messages,
          ticket: 'fixture',
          project: 'one',
          login: 'admin'
        }),
        h(Notes, { ref: notes, ticket: 'fixture', project: 'one' })
      ]
    })
      .provide('openHelp', () => {})
      .directive('window', windowDirective)
      .mount('#app');
    await nextTick();
    window.clipboardFixture = { messages, notes, appearance };
    await messages.value.open('favorites');
  }, vueUrl);
  const hint = 'Press Ctrl+V or use Paste in this field to attach the image.';
  async function pasteImage(field) {
    if (process.env.CLIPBOARD_REAL_KEYBOARD) {
      await field.press('Control+V');
      return;
    }
    await field.evaluate((element) => {
      const transfer = new DataTransfer();
      transfer.items.add(
        new File([new Uint8Array([137, 80, 78, 71])], 'pasted.png', {
          type: 'image/png'
        })
      );
      const event = new ClipboardEvent('paste', {
        bubbles: true,
        cancelable: true
      });
      Object.defineProperty(event, 'clipboardData', { value: transfer });
      element.dispatchEvent(event);
    });
  }
  const messages = page.locator('.messages-dialog');
  const reply = messages.getByLabel('Write a reply', { exact: true });
  await reply.fill('Keep this draft');
  const paste = messages.getByRole('button', {
    name: 'Attach image from clipboard',
    exact: true
  });
  await paste.click();
  await messages.getByRole('status').filter({ hasText: hint }).waitFor();
  assert(await reply.evaluate((element) => element === document.activeElement));
  assert.equal(await reply.inputValue(), 'Keep this draft');
  assert.equal(await messages.locator('[role=alert]').count(), 0);
  if (process.env.CLIPBOARD_CAPTURE) {
    await mkdir(process.env.CLIPBOARD_CAPTURE, { recursive: true });
    await messages.screenshot({
      path: process.env.CLIPBOARD_CAPTURE + '/messages.png'
    });
  }
  await pasteImage(reply);
  await messages
    .getByRole('button', { name: 'Attachments to send', exact: false })
    .waitFor();
  assert.equal(await messages.getByText(hint, { exact: true }).count(), 0);
  assert.equal(await reply.inputValue(), 'Keep this draft');
  // Permission denial follows the same manual-paste path; unexpected/empty failures remain errors.
  await page.evaluate(() =>
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        read: async () => {
          throw new DOMException('Denied', 'NotAllowedError');
        }
      }
    })
  );
  await paste.click();
  await messages.getByText(hint, { exact: true }).waitFor();
  await reply.fill('Draft after denied permission');
  await page.evaluate(() => {
    navigator.clipboard.read = async () => [
      {
        types: ['image/png'],
        getType: async () => new Blob(['png'], { type: 'image/png' })
      }
    ];
  });
  await paste.click();
  assert.equal(await messages.getByText(hint, { exact: true }).count(), 0);
  await page.evaluate(() => {
    navigator.clipboard.read = async () => [{ types: ['text/plain'] }];
  });
  await paste.click();
  await messages
    .getByRole('alert')
    .filter({ hasText: 'The clipboard does not contain an image' })
    .waitFor();
  await page.evaluate(async () => {
    window.clipboardFixture.messages.value.close();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined
    });
    await window.clipboardFixture.notes.value.open(
      { __search_key__: 'demo/item?project=one&code=one', name: 'One' },
      {},
      'publish',
      false
    );
  });
  const notes = page.locator('.notes-panel');
  const note = notes.getByLabel('Note text', { exact: true });
  await note.fill('Keep the note draft');
  await notes
    .getByRole('button', { name: 'Attach image from clipboard', exact: true })
    .click();
  await notes.getByText(hint, { exact: true }).waitFor();
  assert(await note.evaluate((element) => element === document.activeElement));
  assert.deepEqual(await notes.locator('[role=alert]').allTextContents(), []);
  await pasteImage(note);
  await notes
    .locator('.note-attachment')
    .getByText(
      process.env.CLIPBOARD_REAL_KEYBOARD ? 'image.png' : 'pasted.png',
      { exact: true }
    )
    .waitFor();
  assert.equal(await note.inputValue(), 'Keep the note draft');
  await page.evaluate(() => {
    window.clipboardFixture.appearance.language = 'ru';
  });
  await notes
    .getByRole('button', {
      name: 'Вставить изображение из буфера',
      exact: true
    })
    .click();
  for (const width of [1100, 360]) {
    await page.setViewportSize({ width, height: 800 });
    const status = notes.locator('.message-composer-paste-hint');
    await status.waitFor();
    assert((await status.innerText()).includes('Ctrl+V'));
    const bounds = await status.boundingBox();
    assert(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
    if (process.env.CLIPBOARD_CAPTURE) {
      await mkdir(process.env.CLIPBOARD_CAPTURE, { recursive: true });
      await notes.screenshot({
        path: process.env.CLIPBOARD_CAPTURE + '/notes-' + width + '.png'
      });
    }
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS ' +
      (isFirefox ? 'Firefox' : 'Edge') +
      ' messages/notes: LAN HTTP, denied/read/empty clipboard, focused paste, drafts, RU and narrow hint bounds'
  );
} finally {
  await browser?.close();
  await server.close();
}
