import assert from 'node:assert/strict';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { describe } from '../../src/tactic_stream/shared_ui/shell/main_toolbar.ui.mjs';
import { describe as workspaceScene } from '../../src/tactic_stream/shared_ui/shell/workspace.ui.mjs';

const fullWorkspace = process.argv.includes('--workspace');
const root = fileURLToPath(new URL('../../', import.meta.url));
const output =
  root +
  (fullWorkspace
    ? 'tools/frame_workspace/output/'
    : 'tools/frame_foundation/output/main/');
const originalData = JSON.parse(
  await readFile(output + 'original.json', 'utf8')
);
const nativeData = JSON.parse(await readFile(output + 'frame.json', 'utf8'));
const original = fullWorkspace ? originalData.captures : originalData;
const native = fullWorkspace ? nativeData.captures : nativeData;
assert.deepEqual(
  native.map((row) => row.geometry),
  original.map((row) => row.geometry),
  'Preserve the original Handler toolbar'
);
if (fullWorkspace)
  assert.deepEqual(
    native.map((row) => row.workspace),
    original.map((row) => row.workspace),
    'Preserve the original whole workspace bounds'
  );
const russian = JSON.parse(
  await readFile(root + 'frontend/src/locales/ru.json', 'utf8')
);
const configurations = fullWorkspace
  ? ['md3', 'material5', 'fluent'].flatMap((style) =>
      ['en', 'ru'].map((language) => ({ style, language }))
    )
  : [{ style: 'md3', language: 'en' }];
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
  args: ['--disable-lcd-text']
});
const rows = [];
try {
  for (const { style, language } of configurations) {
    const tr = (source) =>
      language === 'ru' ? russian[source] || source : source;
    const page = await browser.newPage({
      viewport: { width: 1280, height: 900 },
      hasTouch: true
    });
    page.setDefaultTimeout(12000);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.addInitScript(
      ({ style, language }) =>
        localStorage.setItem(
          'tactic_stream.appearance',
          JSON.stringify({
            theme: style,
            mode: language === 'en' ? 'dark' : 'light',
            language,
            clickAnimations: false,
            hoverAnimations: false,
            fadeAnimations: false,
            popupAnimations: false
          })
        ),
      { style, language }
    );
    await page.goto(
      process.argv[2] +
        (fullWorkspace
          ? '/projects/admin/'
          : '/projects/admin/?search_type=sthpw/project&view=table')
    );
    await page.getByLabel(tr('Login'), { exact: true }).fill('admin');
    await page
      .getByLabel(tr('Password'), { exact: true })
      .fill('private-test-password');
    await page
      .getByRole('button', { name: tr('Sign in'), exact: true })
      .click();
    await page
      .locator(
        fullWorkspace
          ? '.workspace-empty'
          : '.workspace-results[aria-busy="false"]'
      )
      .waitFor();
    for (const width of [720, 900, 1280, 1920, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.waitForFunction(
        (width) =>
          Math.abs(
            document
              .querySelector('[data-main-control="mainAccount"]')
              .getBoundingClientRect().right -
              (width - (width <= 700 ? 4 : 12))
          ) < 0.01,
        width
      );
      await page.waitForFunction(
        () => !document.querySelector('#topbar-system-activity .busy')
      );
      await page.evaluate(() => document.fonts.ready);
      const scene = describe({
        width,
        compact: width <= 700,
        dccClient: false,
        progressReveal: 0
      });
      const geometry = {};
      const reference = native.find(
        (row) =>
          row.width === width &&
          (!fullWorkspace || (row.style === style && row.language === language))
      );
      for (const node of scene.nodes) {
        if (node.id === 'mainDcc') continue;
        const control = page.locator('[data-main-control="' + node.id + '"]');
        if (node.visible === false) {
          assert.equal(await control.isVisible(), false, node.id);
          continue;
        }
        const bounds = await control.boundingBox();
        assert(bounds, node.id + ' is visible');
        geometry[node.id] = {
          x: bounds.x,
          y: bounds.y,
          width: bounds.width,
          height: bounds.height
        };
        for (const key of ['x', 'y', 'width', 'height'])
          assert(
            Math.abs(bounds[key] - node[key]) < 0.01,
            `${width} ${node.id}.${key}: ${bounds[key]} vs ${node[key]}`
          );
        if (width > 700)
          assert.deepEqual(
            geometry[node.id],
            reference.geometry[node.id],
            'Actual Qt/Vue ' + node.id
          );
      }
      const workspace = {};
      if (fullWorkspace) {
        const outer = workspaceScene(width, 900, width <= 700);
        const selectors = {
          mainToolbarHost: '.topbar',
          mainSectionRailHost: '.workspace-rail',
          mainDockHost: '.workspace-main'
        };
        for (const node of outer.nodes) {
          const host = page.locator(selectors[node.id]);
          if (node.visible === false) {
            assert.equal(await host.count(), 0);
            continue;
          }
          const bounds = await host.boundingBox();
          assert(bounds, node.id);
          workspace[node.id] = {
            x: bounds.x,
            y: bounds.y,
            width: bounds.width,
            height: bounds.height
          };
          for (const key of ['x', 'y', 'width', 'height'])
            assert(
              Math.abs(bounds[key] - node[key]) < 0.1,
              `${style}/${language}/${width} ${node.id}.${key}`
            );
          if (width > 700)
            assert.deepEqual(
              workspace[node.id],
              reference.workspace[node.id],
              'Actual complete Qt/Vue host ' + node.id
            );
        }
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth
          ),
          true,
          'The shell fits the phone'
        );
      }
      await page.getByLabel(tr('More options'), { exact: true }).click();
      await page.locator('.settings-menu[open]').waitFor();
      await page.keyboard.press('Escape');
      await page.mouse.move(0, 200);
      await page.getByLabel(tr('Account'), { exact: true }).tap();
      await page.locator('.account-menu[open]').waitFor();
      assert.equal(
        await page
          .locator('.account-menu > summary')
          .evaluate((item) => getComputedStyle(item).webkitTapHighlightColor),
        'rgba(0, 0, 0, 0)',
        'House-control feedback must not receive an extra rectangular browser tap overlay'
      );
      await page.keyboard.press('Escape');
      assert.equal(
        await page.locator('.account-menu').evaluate((menu) => menu.open),
        false,
        'Escape closes the actual account menu'
      );
      await page.getByLabel(tr('Project'), { exact: true }).click();
      await page.locator('#project-chooser:popover-open').waitFor();
      await page.keyboard.press('Escape');
      await page.mouse.move(0, 200);
      await page.evaluate(() => document.activeElement?.blur());
      if (width >= 900) {
        const dot = await page.locator('.topbar .connection-dot').boundingBox();
        assert.equal(
          dot.width,
          8,
          'The connection dot must not shrink around a translated caption'
        );
        assert.equal(dot.height, 8);
      }
      const screenshot = fullWorkspace
        ? `stream-${style}-${language}-${width}.png`
        : `stream-${width}.png`;
      await page.screenshot({
        path: output + screenshot,
        ...(fullWorkspace ? {} : { clip: { x: 0, y: 0, width, height: 44 } })
      });
      const background = await page.evaluate(() => {
        const canvas = document.createElement('canvas'),
          ctx = canvas.getContext('2d');
        canvas.width = canvas.height = 1;
        ctx.fillStyle = getComputedStyle(
          document.documentElement
        ).backgroundColor;
        ctx.fillRect(0, 0, 1, 1);
        return (
          '#' +
          [...ctx.getImageData(0, 0, 1, 1).data]
            .slice(0, 3)
            .map((value) => value.toString(16).padStart(2, '0'))
            .join('')
        );
      });
      if (fullWorkspace)
        assert.equal(
          background,
          native.find((row) => row.style === style && row.language === language)
            .background
        );
      rows.push({
        width,
        height: 900,
        style,
        language,
        geometry,
        workspace,
        background,
        avatarColor: await page
          .locator('.topbar .account-avatar')
          .evaluate((item) => {
            const canvas = document.createElement('canvas'),
              ctx = canvas.getContext('2d');
            ctx.fillStyle = getComputedStyle(item).color;
            ctx.fillRect(0, 0, 1, 1);
            return (
              '#' +
              [...ctx.getImageData(0, 0, 1, 1).data]
                .slice(0, 3)
                .map((value) => value.toString(16).padStart(2, '0'))
                .join('')
            );
          }),
        screenshot
      });
    }
    assert.deepEqual(errors, []);
    await page.close();
  }
  let payload = rows;
  if (fullWorkspace) {
    const sources = {};
    const paths = [
      'frontend/src/App.vue',
      'frontend/src/style.css',
      'frontend/src/mobile.js',
      'frontend/src/features/workspace/DockWorkspace.vue',
      'frontend/tests/frame_main_browser.mjs',
      'tools/frame_foundation/main_qml.py'
    ];
    for (const name of await readdir(root + 'src/tactic_stream/web/assets'))
      if (/\.(js|css)$/.test(name))
        paths.push('src/tactic_stream/web/assets/' + name);
    for (const path of paths)
      sources[path] = createHash('sha256')
        .update(await readFile(root + path))
        .digest('hex');
    payload = { captures: rows, sources };
  }
  await writeFile(output + 'stream.json', JSON.stringify(payload, null, 2));
  console.log(
    `Main ${fullWorkspace ? 'workspace' : 'toolbar'}: original Qt = Frame Qt = actual Vue geometry; settings/account/project mouse and touch at ${rows.length} states passed`
  );
} finally {
  await browser.close();
}
