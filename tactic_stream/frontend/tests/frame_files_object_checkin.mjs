import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
let server, browser;
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
    viewport: { width: 1100, height: 900 }
  });
  const errors = [];
  const appends = [];
  let uploads = 0;
  let appendResponse = 'saved';
  const uploadDirectory = 'append_' + 'a'.repeat(32);
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/admin/**', async (route) => {
    if (route.request().url().endsWith('/admin/result-items')) {
      await route.fulfill({
        json: {
          result: {
            items: [
              {
                branches: [
                  { kind: 'process', process: 'publish', title: 'Publish' },
                  { kind: 'process', process: 'model', title: 'Model' }
                ]
              }
            ]
          }
        }
      });
      return;
    }
    assert(route.request().url().endsWith('/admin/rpc'));
    const payload = route.request().postDataJSON();
    if (
      payload.method === 'execute_cmd' &&
      payload.args[1] === 'tactic.ui.table.TableSnapshotAppendCmd'
    ) {
      const values = payload.args[2];
      if (values.action === 'save') {
        appends.push(values);
        await route.fulfill({
          json: {
            result: {
              info: {
                state: appendResponse,
                searchKey: 'sthpw/snapshot?code=S7'
              }
            }
          }
        });
      } else {
        assert.equal(values.search_key, 'sthpw/snapshot?code=S7');
        await route.fulfill({
          json: {
            result: {
              info: {
                searchKey: 'sthpw/snapshot?code=S7',
                snapshotCode: 'S7',
                version: 7,
                expectedRevision: 'revision-seven',
                uploadDirectory,
                existingNames: ['original.txt'],
                ownerKey: 'cg/asset?code=ROBOT001',
                ownerTitle: 'Hero Robot',
                process: 'publish',
                context: 'publish/reference'
              }
            }
          }
        });
      }
      return;
    }
    assert.equal(payload.method, 'get_base_dirs');
    await route.fulfill({ json: { result: {} } });
  });
  await page.route('**/UploadServer/', (route) => {
    uploads++;
    assert.match(route.request().postData(), new RegExp(uploadDirectory));
    return route.fulfill({ json: ['reference.txt'] });
  });
  await page.goto(server.resolvedUrls.local[0] + 'tools/frame_files/');
  await page.waitForFunction(() => window.filesFixture);
  const dialog = page.locator('.object-checkin[open]');
  const field = (id) => dialog.locator('[data-frame=' + id + ']');
  async function show(options = {}, width = 760) {
    await page.evaluate((value) => window.filesFixture.show(value), {
      screen: 'object-checkin',
      width,
      height: 800,
      style: 'md3',
      dark: true,
      language: 'en',
      options,
      model: {}
    });
    await dialog
      .locator('.object-checkin-workspace[aria-busy=false]')
      .waitFor();
  }
  const files = ['one.txt', 'two.txt', 'three.txt'].map((name) => ({
    name,
    mimeType: 'text/plain',
    buffer: Buffer.from(name)
  }));
  await show();
  await dialog.locator('input[type=file]').setInputFiles(files);
  await field('objectCheckinFileRemove_1').click();
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().files.length),
    2
  );
  await field('objectCheckinField_context').fill('publish/review');
  await field('objectCheckinDescription').fill('Prepared with shared controls');
  await field('objectCheckinKeepNameText').waitFor();
  const originalKeepName = await page.evaluate(
    () => window.filesFixture.checkin().keepFileName
  );
  const switchText = await field('objectCheckinKeepNameText').boundingBox();
  await page.mouse.click(
    switchText.x + switchText.width / 2,
    switchText.y + switchText.height / 2
  );
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().keepFileName),
    !originalKeepName,
    'Caption clicks toggle the same primitive switch'
  );
  await field('multiFileCheckinSeparateButton').click();
  await page.evaluate(() => {
    window.originalCheckinFiles = [...window.filesFixture.checkin().files];
  });
  await field('objectCheckinSubmit').click();
  await dialog.waitFor({ state: 'hidden' });
  assert.deepEqual(
    await page.evaluate(() =>
      window.filesFixture
        .events()
        .filter((event) => event.type === 'queue')
        .map((event) => ({
          names: event.value.files.map((file) => file.name),
          context: event.value.context,
          description: event.value.description
        }))
    ),
    [
      {
        names: ['one.txt'],
        context: 'publish/review',
        description: 'Prepared with shared controls'
      },
      {
        names: ['three.txt'],
        context: 'publish/review',
        description: 'Prepared with shared controls'
      }
    ]
  );
  assert.equal(
    await page.evaluate(
      () =>
        window.filesFixture.events()[0].value.files[0] ===
        window.originalCheckinFiles[0]
    ),
    true,
    'Queue handoff retains the selected File'
  );
  await show({ revision: true });
  const revision = page.locator('.object-revision-confirmation[open]');
  await revision.waitFor();
  assert.equal(await revision.evaluate((el) => el.matches(':modal')), true);
  await page.keyboard.press('Escape');
  assert.equal(await revision.isVisible(), true);
  await revision.locator('[data-frame=revisionCheckinCancel]').click();
  await dialog.waitFor({ state: 'hidden' });
  assert.equal(
    await page.evaluate(() => window.filesFixture.events().length),
    0
  );
  await show({ revision: true });
  await revision.locator('[data-frame=revisionCheckinAccept]').click();
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().confirmed),
    true
  );
  await dialog.locator('input[type=file]').setInputFiles([files[0]]);
  await field('objectCheckinSubmit').click();
  assert.equal(
    await page.evaluate(() => window.filesFixture.events()[0].value.isRevision),
    true
  );
  await show({ preview: true });
  await dialog.locator('input[type=file]').setInputFiles([files[0]]);
  await field('objectCheckinErrorText').waitFor();
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().files.length),
    0
  );
  await dialog.locator('input[type=file]').setInputFiles([
    {
      name: 'preview.png',
      mimeType: 'image/png',
      buffer: Buffer.from('fixture')
    }
  ]);
  await field('objectCheckinSubmit').click();
  assert.equal(
    await page.evaluate(() => window.filesFixture.events()[0].value.context),
    'icon'
  );
  await page.setViewportSize({ width: 390, height: 780 });
  await show({}, 390);
  await dialog.locator('input[type=file]').setInputFiles(files);
  await field('objectCheckinCancel').click();
  await field('objectCheckinDiscardNoticeText').waitFor();
  await field('objectCheckinContinue').click();
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().files.length),
    3
  );
  await field('objectCheckinCancel').click();
  await field('objectCheckinDiscard').click();
  await dialog.waitFor({ state: 'hidden' });
  await page.setViewportSize({ width: 1100, height: 960 });
  await page.evaluate(async () => {
    const { preferences } = await import(
      '/frontend/src/features/configuration/preferences.js'
    );
    preferences.checkin.keepFilename = true;
  });
  await show({ append: true });
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().keepFileName),
    false,
    'Append defaults match the native window independently of new check-in preferences'
  );
  assert.equal(
    await dialog.getAttribute('data-window-kind'),
    'snapshot_append'
  );
  const body = await dialog.locator('.object-checkin-workspace').boundingBox();
  assert.equal(
    body.width,
    760,
    'Browser content width matches the native window client area'
  );
  assert.equal(
    body.height,
    820,
    'Browser chrome must not consume the native form viewport'
  );
  await dialog.locator('input[type=file]').setInputFiles([
    {
      name: 'reference.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('keep original source')
    }
  ]);
  await field('objectCheckinField_fileType').fill('');
  await field('objectCheckinSubmit').click();
  await field('objectCheckinErrorText')
    .filter({ hasText: 'Choose a valid file type' })
    .waitFor();
  assert.equal(uploads, 0, 'Invalid file types are rejected before uploading');
  await field('objectCheckinField_fileType').fill('reference');
  await field('objectCheckinKeepName').getByRole('switch').click();
  await field('objectCheckinSubmit').click();
  await dialog.waitFor({ state: 'hidden' });
  assert.deepEqual(appends, [
    {
      action: 'save',
      search_key: 'sthpw/snapshot?code=S7',
      expected_revision: 'revision-seven',
      filenames: ['reference.txt'],
      file_type: 'reference',
      keep_file_name: true,
      upload_directory: uploadDirectory
    }
  ]);
  appendResponse = 'unknown';
  await show({ append: true });
  await dialog.locator('input[type=file]').setInputFiles([files[0]]);
  await field('objectCheckinSubmit').click();
  await field('objectCheckinUnknownText').waitFor();
  assert.equal(
    await field('objectCheckinSubmit').isEnabled(),
    false,
    'Unknown writes must never be repeated'
  );
  assert.equal(appends.length, 2);
  await field('objectCheckinCancel').click();
  await field('objectCheckinDiscard').click();
  await dialog.waitFor({ state: 'hidden' });
  await show({ append: true });
  await dialog.evaluate((node) => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['directory entry'], 'folder'));
    const event = new DragEvent('drop', {
      bubbles: true,
      cancelable: true,
      dataTransfer: transfer
    });
    Object.defineProperty(transfer, 'items', {
      value: [{ webkitGetAsEntry: () => ({ isDirectory: true }) }]
    });
    node.dispatchEvent(event);
  });
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().files.length),
    0
  );
  await field('objectCheckinErrorText').waitFor();
  await dialog.locator('input[type=file]').setInputFiles(
    Array.from({ length: 51 }, (_, index) => ({
      name: `limit-${index}.txt`,
      mimeType: 'text/plain',
      buffer: Buffer.from('limit')
    }))
  );
  assert.equal(
    await page.evaluate(() => window.filesFixture.checkin().files.length),
    0,
    'The file limit rejects the whole selection'
  );
  await field('objectCheckinField_fileType').focus();
  await field('objectCheckinField_fileType').evaluate((node) => {
    for (let index = 0; index < 2; index++) {
      const transfer = new DataTransfer();
      transfer.items.add(
        new File(['clipboard ' + index], 'image.png', { type: 'image/png' })
      );
      node.dispatchEvent(
        new ClipboardEvent('paste', {
          bubbles: true,
          cancelable: true,
          clipboardData: transfer
        })
      );
    }
  });
  const clipboard = await page.evaluate(async () =>
    Promise.all(
      window.filesFixture.checkin().files.map(async (file) => ({
        name: file.name,
        text: await file.text()
      }))
    )
  );
  assert.equal(clipboard.length, 2);
  assert.notEqual(
    clipboard[0].name,
    clipboard[1].name,
    'Clipboard images have distinct upload identities'
  );
  assert.deepEqual(
    clipboard.map((item) => item.text),
    ['clipboard 0', 'clipboard 1']
  );
  await field('objectCheckinCancel').click();
  await field('objectCheckinDiscard').click();
  await dialog.waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  console.log(
    'Object Check-in actual input: individual File identity handoff, context/description, explicit revision cancel/accept, preview validation and phone discard guard passed.'
  );
} finally {
  await browser?.close();
  await server?.close();
}
