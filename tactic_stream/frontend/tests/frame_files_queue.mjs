import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const fixture = JSON.parse(
  await readFile(root + 'tools/frame_files/fixture.json', 'utf8')
);
const writes = [],
  errors = [];
let server, browser;
let holdPlan = false,
  releasePlan;
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
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
    viewport: { width: 1100, height: 800 }
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/**', async (route) => {
    const payload = route.request().postDataJSON();
    if (payload.method === 'get_base_dirs') {
      await route.fulfill({ json: { result: {} } });
      return;
    }
    assert.equal(payload.method, 'execute_cmd');
    assert.equal(
      payload.args[1],
      'tactic.command.browser_checkin_cmd.BrowserCheckinCmd'
    );
    const value = payload.args[2];
    assert.equal(value.action, 'plan');
    if (holdPlan) {
      holdPlan = false;
      await new Promise((resolve) => (releasePlan = resolve));
    }
    writes.push(value);
    await route.fulfill({
      json: {
        result: {
          info: {
            plan: {
              version: value.version || 1,
              files: value.source_files.map((file, index) => ({
                title: file.path,
                indices: [index],
                versioned: ['repo/v001/' + file.path],
                versionless: ['repo/latest/' + file.path]
              }))
            }
          }
        }
      }
    });
  });
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_files/');
  await page.waitForFunction(() => window.filesFixture);
  const value = {
    screen: 'queue',
    width: 1000,
    height: 700,
    style: 'md3',
    dark: true,
    language: 'en',
    model: {
      ...fixture,
      queue: [0, 1].map((index) => ({
        name: 'source_' + index + '.txt',
        title: 'Asset ' + index,
        files: ['source_' + index + '.txt'],
        context: 'publish',
        process: 'publish',
        version: 0,
        description: ''
      }))
    }
  };
  await page.evaluate((value) => window.filesFixture.show(value), value);
  const queue = page.locator('.commit-queue-workspace');
  await queue.locator('[data-frame=commitQueueSelect_1]').waitFor();
  const field = (id) => queue.locator('[data-frame=' + id + ']');
  await page.evaluate(async () => {
    const owner = window.filesFixture.queue();
    window.actualResizeDispatch = owner.dispatch;
    window.resizeActions = [];
    owner.dispatch = (action) => {
      if (action.type.startsWith('paneWidth'))
        window.resizeActions.push({ type: action.type, value: action.value });
      return window.actualResizeDispatch(action);
    };
    owner.$forceUpdate();
    await owner.$nextTick();
  });
  let grip = await field('commitQueueMainSplitter').boundingBox();
  const point = { x: grip.x + grip.width / 2, y: grip.y + grip.height / 2 };
  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  await page.mouse.move(point.x + 40, point.y, { steps: 4 });
  await page.evaluate(() =>
    window.dispatchEvent(new PointerEvent('pointerup', { pointerId: 999 }))
  );
  assert.ok(
    await page.evaluate(() =>
      window.resizeActions.some((action) => action.type === 'paneWidthDraft')
    )
  );
  assert.equal(
    await page.evaluate(
      () =>
        window.resizeActions.filter((action) => action.type === 'paneWidth')
          .length
    ),
    0
  );
  await page.mouse.up();
  assert.equal(
    await page.evaluate(
      () =>
        window.resizeActions.filter((action) => action.type === 'paneWidth')
          .length
    ),
    1
  );
  const committedWidth = (await field('commitQueueListSlot').boundingBox())
    .width;
  grip = await field('commitQueueMainSplitter').boundingBox();
  await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
  await page.mouse.down();
  await page.mouse.move(grip.x - 25, grip.y + grip.height / 2, { steps: 3 });
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await page.mouse.up();
  await page.waitForFunction(
    (width) =>
      Math.abs(
        document
          .querySelector('[data-frame=commitQueueListSlot]')
          .getBoundingClientRect().width - width
      ) < 0.1,
    committedWidth
  );
  assert.equal(
    await page.evaluate(
      () =>
        window.resizeActions.filter(
          (action) => action.type === 'paneWidthCancel'
        ).length
    ),
    1
  );
  await field('commitQueueMainSplitter').focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(
    await page.evaluate(
      () =>
        window.resizeActions.filter((action) => action.type === 'paneWidth')
          .length
    ),
    2
  );
  await page.evaluate(async () => {
    const owner = window.filesFixture.queue();
    owner.dispatch = window.actualResizeDispatch;
    owner.$forceUpdate();
    await owner.$nextTick();
  });
  await field('commitQueueCheck_1').getByRole('checkbox').uncheck();
  assert.equal(
    await page.evaluate(() => window.filesFixture.queue().jobs[0].checked),
    false
  );
  await field('commitQueueSelect_1').click();
  await page.keyboard.press('ArrowDown');
  assert.equal(
    await page.evaluate(() => window.filesFixture.queue().selectedId),
    2
  );
  await page.keyboard.press('Home');
  assert.equal(
    await page.evaluate(() => window.filesFixture.queue().selectedId),
    1
  );
  await field('commitQueueAdvancedToggle').click();
  await field('commitQueueField_version').fill('bad');
  await page.keyboard.press('Tab');
  await field('commitQueueVersionError').waitFor();
  assert.equal(
    await page.evaluate(() => window.filesFixture.queue().jobs[0].version),
    0
  );
  assert.equal(await field('commitQueuePrimarySendButton').isDisabled(), true);
  await field('commitQueueField_version').fill('12');
  await page.keyboard.press('Enter');
  await page.waitForFunction(
    () => window.filesFixture.queue().selected.version === 12
  );
  await field('commitQueueContextChip').click();
  await field('commitQueueContextField').fill('review');
  await page.keyboard.press('Enter');
  await page.waitForFunction(
    () => window.filesFixture.queue().selected.context === 'publish/review'
  );
  const description = queue.getByRole('textbox', {
    name: 'Description',
    exact: true
  });
  await description.fill('Queue description');
  await description.press('Tab');
  await page.waitForFunction(
    () =>
      window.filesFixture.queue().selected.description === 'Queue description'
  );
  await page.waitForFunction(() =>
    window.filesFixture.queue().jobs.every((job) => !job.validating)
  );
  await page.evaluate(() => {
    const owner = window.filesFixture.queue();
    window.actualQueueRun = owner.run;
    owner.run = (jobs) => {
      window.requestedQueueIds = jobs.map((job) => job.id);
    };
  });
  await field('commitQueuePrimarySendButton').click();
  assert.deepEqual(
    await page.evaluate(() => window.requestedQueueIds),
    [1, 2],
    'Commit all includes unchecked operations'
  );
  await field('commitQueueSendOverflowButton').click();
  await page
    .locator('.commit-queue-action-menu[open] > .account-panel')
    .getByRole('button', { name: 'Commit selected', exact: true })
    .click();
  assert.deepEqual(await page.evaluate(() => window.requestedQueueIds), [2]);
  await page.evaluate(() => {
    window.filesFixture.queue().run = window.actualQueueRun;
  });
  await field('commitQueueMenu_1').click();
  await page
    .locator('.commit-queue-action-menu[open] > .account-panel')
    .waitFor();
  await page.keyboard.press('Escape');
  await field('commitQueueTool_clear').click();
  const clear = page.locator('.commit-queue-clear-dialog[open]');
  await clear.waitFor();
  const bounds = await clear.boundingBox();
  assert.equal(Math.round(bounds.width), 420);
  for (const [key, expected] of Object.entries({ x: 290, y: 208, height: 284 }))
    assert(
      Math.abs(bounds[key] - expected) < 0.1,
      'House dialog ' + key + ': ' + bounds[key]
    );
  const contentBounds = await clear
    .locator('.app-dialog-content > div')
    .boundingBox();
  assert.equal(contentBounds.y - bounds.y, 94);
  assert.equal(contentBounds.x - bounds.x, 20);
  assert.equal(contentBounds.width, 380);
  assert.equal(await clear.evaluate((el) => el.matches(':modal')), true);
  await page.keyboard.press('Escape');
  await page.waitForFunction(
    () => document.activeElement?.dataset.frame === 'commitQueueTool_clear'
  );
  assert.equal(
    await page.evaluate(() => window.filesFixture.queue().jobs.length),
    2
  );
  await page.evaluate(() =>
    window.filesFixture.queue().addPreviews([
      new File([new Uint8Array([1, 2, 3])], 'preview.png', {
        type: 'image/png'
      })
    ])
  );
  await page.waitForFunction(
    () => window.filesFixture.queue().selected.previews.length === 1
  );
  await field('commitQueuePreviewButton').click();
  const previews = page.locator('.commit-queue-previews-dialog[open]');
  await previews.waitFor();
  assert.equal(await previews.evaluate((el) => el.matches(':modal')), false);
  await previews.locator('[data-frame=commitQueuePreviewsClose]').click();
  await previews.waitFor({ state: 'hidden' });
  await page.evaluate(async () => {
    const owner = window.filesFixture.queue();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        read: () =>
          new Promise((resolve) => {
            window.completeQueueClipboard = () =>
              resolve([
                {
                  types: ['image/png'],
                  getType: async () =>
                    new Blob(['clipboard'], { type: 'image/png' })
                }
              ]);
          })
      }
    });
    window.queueClipboardRequest = owner.pasteImage();
    await owner.select(owner.jobs[1], false);
  });
  await page.evaluate(async () => {
    window.completeQueueClipboard();
    await window.queueClipboardRequest;
  });
  assert.equal(
    await page.evaluate(
      () => window.filesFixture.queue().jobs[1].previews.length
    ),
    0,
    'Delayed clipboard belongs to the original operation'
  );
  await page.evaluate(async () => {
    const owner = window.filesFixture.queue();
    window.queueClipboardRequest = owner.pasteImage();
    await window.filesFixture.session({ ticket: 'renewed-fixture' });
    window.completeQueueClipboard();
    await window.queueClipboardRequest;
  });
  assert.equal(
    await page.evaluate(
      () => window.filesFixture.queue().selected.previews.length
    ),
    0,
    'Clipboard cannot cross an authentication session even for the same user and operation'
  );
  await page.evaluate(() => {
    const owner = window.filesFixture.queue();
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getDisplayMedia: () =>
          new Promise(
            (resolve) =>
              (window.completeQueueCapture = () =>
                resolve({
                  getTracks: () => [
                    { stop: () => (window.queueCaptureStopped = true) }
                  ]
                }))
          )
      }
    });
    window.queueCaptureRequest = owner.capture();
  });
  await page.evaluate(async () => {
    await window.filesFixture.session({ ticket: 'renewed-again' });
    window.completeQueueCapture();
    await window.queueCaptureRequest;
  });
  assert.equal(
    await page.evaluate(() => window.queueCaptureStopped),
    true,
    'An abandoned capture releases every screen stream'
  );
  for (const width of [680, 390, 1000]) {
    await page.evaluate((width) => {
      document.querySelector('#files-fixture').style.width = width + 'px';
    }, width);
    await page.waitForFunction(
      (width) => window.filesFixture.queue().queueSize.width === width,
      width
    );
    assert((await queue.boundingBox()).width <= width);
  }
  await page.evaluate(() => {
    const owner = window.filesFixture.queue(),
      first = owner.jobs[0];
    owner.jobs = Array.from({ length: 1000 }, (_, index) => ({
      ...first,
      id: index + 1,
      name: 'Virtual ' + index
    }));
    owner.selectedId = 1;
  });
  await page.waitForTimeout(50);
  assert(
    (await queue.locator('[data-frame^=commitQueueSelect_]').count()) < 30
  );
  holdPlan = true;
  await page.evaluate(() => {
    const owner = window.filesFixture.queue();
    owner.jobs = [owner.jobs[0]];
    window.delayedQueueValidation = owner.validateAll();
  });
  const deadline = Date.now() + 5000;
  while (!releasePlan && Date.now() < deadline) await page.waitForTimeout(10);
  assert.ok(releasePlan, 'Validation reached the delayed transport');
  await page.evaluate(() =>
    window.filesFixture.session({ login: 'other-user', ticket: 'other-ticket' })
  );
  releasePlan();
  await page.evaluate(() => window.delayedQueueValidation);
  assert.equal(
    await page.evaluate(() => window.filesFixture.queue().jobs.length),
    0,
    'Late validation cannot restore another user’s files'
  );
  assert.equal(
    await page.evaluate(() =>
      localStorage.getItem('tactic_stream.commit_queue.other-user')
    ),
    null,
    'Late callbacks cannot write the old queue into the next account’s journal'
  );
  assert.deepEqual(errors, []);
  assert(writes.length > 0);
  console.log(
    'Commit Queue real input: options, drafts, keyboard, menus, short modal/nonmodal hosts, resize and 1000-row virtualization passed.'
  );
} finally {
  await browser?.close();
  await server?.close();
}
