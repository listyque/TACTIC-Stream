import assert from 'node:assert/strict';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import {
  popup,
  category,
  keyTarget
} from '../../src/tactic_stream/shared_ui/shell/projects.ui.mjs';
import { key } from '../../src/tactic_stream/shared_ui/controls/tabs/workspace.ui.mjs';
const root = fileURLToPath(new URL('../../', import.meta.url)),
  out = root + 'tools/frame_projects/output/';
assert.equal(popup(320, 760, true).width, 296);
assert.equal(category(260, 7, true).columns, 1);
assert.equal(keyTarget(['a', 'b', 'c'], 'a', 'ArrowDown', 3), 'c');
assert.deepEqual(key([{ id: 'a' }, { id: 'b' }], 'b', 'ArrowRight'), {
  type: 'select',
  id: 'a'
});
assert.equal(key([{ id: 'a', closable: false }], 'a', 'Delete'), null);
const server = await createServer({
  root,
  configFile: false,
  plugins: [vue()],
  resolve: {
    alias: {
      vue: root + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars'],
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge',
    args: ['--disable-lcd-text']
  });
  const page = await browser.newPage({
    viewport: { width: 900, height: 800 },
    hasTouch: true
  });
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(
    'http://127.0.0.1:' +
      server.httpServer.address().port +
      '/tools/frame_projects/index.html'
  );
  await page.waitForFunction(() => !!window.projectsHarness);
  await page.evaluate(() => document.fonts.ready);
  const captures = [];
  if (process.argv.includes('--capture')) {
    const native = JSON.parse(await readFile(out + 'native.json', 'utf8'));
    for (const sample of native.captures.filter((row) => !row.original)) {
      await page.mouse.move(1000, 1000);
      await page.setViewportSize(
        sample.kind === 'chooser'
          ? { width: 900, height: 800 }
          : sample.kind === 'card'
            ? { width: 248, height: 258 }
            : sample.kind === 'rail'
              ? { width: 400, height: 260 }
              : { width: 180, height: 50 }
      );
      await page.evaluate(async (row) => {
        await window.projectsHarness.configure(
          row.kind,
          row.style,
          row.language,
          row.kind === 'card' && row.variant === 1,
          row.kind === 'tab'
            ? {
                current: row.variant === 1,
                hovered: row.variant === 2,
                dirty: row.variant === 2
              }
            : {}
        );
      }, sample);
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))
          )
      );
      if (sample.kind === 'rail') {
        await page.mouse.move(390, 250);
        if (sample.variant) {
          await page.mouse.move(20, sample.variant === 1 ? 28 : 73);
          await page.waitForTimeout(180);
          if (sample.variant === 3) await page.mouse.down();
        }
      }
      await page.evaluate(() => document.fonts.ready);
      const boxes = await page
        .locator('[data-frame]')
        .evaluateAll((items, sample) => {
          const result = {};
          for (const item of items) {
            const name = item.dataset.frame;
            if (sample.kind === 'rail') {
              const row = item.closest('.section-tab-row');
              if (
                row &&
                row.dataset.sectionId !==
                  (sample.variant > 1 ? 'shots' : 'assets')
              )
                continue;
            }
            if (
              ![
                'projectChooserTitle',
                'projectChooserSummary',
                'projectChooserDivider',
                'projectGridPreview',
                'projectCardTitle',
                'projectCardDescription',
                'projectCardCategory',
                'projectCardType',
                'workspaceTabSelectionIndicator',
                'workspaceTabSelectionLabel',
                'sectionTabSurface',
                'sectionTabBadge',
                'sectionTabTitle',
                'sectionTabIcon',
                'sectionRailBackground'
              ].includes(name) ||
              getComputedStyle(item).display === 'none'
            )
              continue;
            const box = item.getBoundingClientRect();
            result[name] = {
              x: box.x,
              y: box.y,
              width: box.width,
              height: box.height
            };
          }
          const close = document.querySelector(
            '.section-tab-reveal:popover-open:not(.section-tab-reveal-actions) > .icon-button'
          );
          if (close) {
            const box = close.getBoundingClientRect();
            result.sectionTabCloseButton = {
              x: box.x,
              y: box.y,
              width: box.width,
              height: box.height
            };
          }
          return result;
        }, sample);
      const { paints, rounding } = await page
        .locator('[data-frame]')
        .evaluateAll((items, sample) => {
          const canvas = document.createElement('canvas'),
            ctx = canvas.getContext('2d'),
            colors = {},
            rounding = {};
          canvas.width = canvas.height = 1;
          for (const item of items) {
            const row = item.closest('.section-tab-row');
            if (
              sample.kind === 'rail' &&
              row &&
              row.dataset.sectionId !==
                (sample.variant > 1 ? 'shots' : 'assets')
            )
              continue;
            const style = getComputedStyle(item),
              background = item.classList.contains('frame-box');
            if (item.dataset.frame === 'sectionTabBadge')
              rounding.sectionTabBadge = [
                'borderTopLeftRadius',
                'borderTopRightRadius',
                'borderBottomRightRadius',
                'borderBottomLeftRadius'
              ].map((corner) => parseFloat(style[corner]));
            ctx.clearRect(0, 0, 1, 1);
            ctx.fillStyle = background ? style.backgroundColor : style.color;
            ctx.fillRect(0, 0, 1, 1);
            colors[item.dataset.frame] =
              '#' +
              [...ctx.getImageData(0, 0, 1, 1).data]
                .slice(0, 3)
                .map((value) => value.toString(16).padStart(2, '0'))
                .join('');
          }
          return { paints: colors, rounding };
        }, sample);
      const image = 'browser-' + sample.id + '.png';
      await page.screenshot({ path: out + image, animations: 'disabled' });
      captures.push({ id: sample.id, boxes, paints, rounding, image });
      if (sample.kind === 'rail' && sample.variant === 3) await page.mouse.up();
    }
    const sources = {};
    for (const path of [
      'frontend/src/features/projects/ProjectChooser.vue',
      'frontend/src/features/projects/ProjectCard.vue',
      'frontend/src/controls/WorkspaceTabs.vue',
      'frontend/src/controls/WorkspaceTabVisual.vue',
      'frontend/src/controls/SectionTabVisual.vue',
      'frontend/src/controls/SectionTabRail.vue',
      'frontend/src/appearance.js',
      'frontend/src/frame/FrameView.vue',
      'frontend/src/style.css',
      'frontend/src/frame/frame.css',
      'frontend/src/controls/AppButton.vue',
      'frontend/src/controls/AppIcon.vue',
      'frontend/src/controls/ItemPreview.vue',
      'frontend/src/theme.css',
      'frontend/src/locales/ru.json',
      'frontend/src/locales/en.json',
      'tools/frame_projects/ProjectsHarness.vue',
      'tools/frame_projects/projects.entry.js',
      'frontend/tests/frame_projects.mjs'
    ])
      sources[path] = createHash('sha256')
        .update(await readFile(root + path))
        .digest('hex');
    await writeFile(
      out + 'browser.json',
      JSON.stringify({ captures, sources }, null, 2)
    );
  }
  await page.setViewportSize({ width: 900, height: 800 });
  await page.evaluate(() =>
    window.projectsHarness.configure('chooser', 'md3', 'en')
  );
  const chooser = page.locator('#project-chooser');
  assert.equal(await chooser.locator('[data-project]').count(), 3);
  await chooser.getByRole('checkbox', { name: 'Retired', exact: true }).check();
  assert.equal(await chooser.locator('[data-project]').count(), 4);
  await chooser
    .getByRole('checkbox', { name: 'Templates', exact: true })
    .check();
  await chooser
    .getByRole('checkbox', { name: 'Built-in', exact: true })
    .check();
  assert.equal(await chooser.locator('[data-project]').count(), 6);
  const first = chooser.getByRole('button', {
    name: 'Project one',
    exact: true
  });
  await first.focus();
  await page.keyboard.press('End');
  assert.equal(
    await page.evaluate(() =>
      document.activeElement.getAttribute('aria-label')
    ),
    'Built-in project'
  );
  await page.keyboard.press('Home');
  await page.keyboard.press('Space');
  assert.equal(await page.evaluate(() => window.projectsHarness.calls), 1);
  assert.equal(
    await chooser.evaluate((node) => node.matches(':popover-open')),
    false
  );
  await page.setViewportSize({ width: 320, height: 760 });
  await page.evaluate(() =>
    window.projectsHarness.configure('chooser', 'md3', 'ru')
  );
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  assert((await chooser.boundingBox()).width <= 320);
  assert.equal(
    await chooser
      .getByRole('checkbox', { name: 'Шаблоны', exact: true })
      .count(),
    1
  );
  assert(
    await chooser.evaluate((node) => node.scrollWidth <= node.clientWidth)
  );
  const titleBox = await chooser
    .locator('[data-frame="projectChooserSummary"]')
    .boundingBox();
  const filterBoxes = await chooser.getByRole('checkbox').evaluateAll((nodes) =>
    nodes.map((node) => {
      const box = node.getBoundingClientRect();
      return { top: box.top, bottom: box.bottom };
    })
  );
  assert(filterBoxes.every((box) => box.top >= titleBox.y + titleBox.height));
  await chooser.getByRole('button', { name: 'Project two', exact: true }).tap();
  assert.equal(await page.evaluate(() => window.projectsHarness.calls), 2);
  await page.evaluate(() =>
    window.projectsHarness.configure('inline', 'md3', 'en')
  );
  await page.getByRole('button', { name: 'Project one', exact: true }).tap();
  assert.equal(await page.evaluate(() => window.projectsHarness.calls), 3);
  await page.setViewportSize({ width: 800, height: 600 });
  await page.evaluate(() =>
    window.projectsHarness.configure('input', 'md3', 'en')
  );
  const tabs = page.getByRole('tablist', { name: 'Search tabs' });
  await tabs.getByRole('tab', { name: 'Assets', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.evaluate(() => window.projectsHarness.current), 'b');
  await page.keyboard.press('Control+Shift+ArrowRight');
  assert.deepEqual(
    await page.evaluate(() => window.projectsHarness.tabs.map((tab) => tab.id)),
    ['a', 'c', 'b']
  );
  await page.keyboard.press('Delete');
  assert.equal(
    await page.evaluate(() => window.projectsHarness.tabs.length),
    2
  );
  assert.equal(
    await tabs
      .getByRole('tab', { selected: true })
      .evaluate((node) => node === document.activeElement),
    true
  );
  await page.setViewportSize({ width: 400, height: 260 });
  await page.evaluate(async () => {
    await window.projectsHarness.configure('rail', 'md3', 'en');
    window.projectsHarness.resetSections();
  });
  const sectionTabs = page.getByRole('tablist', { name: 'Open sections' });
  assert.deepEqual(
    await sectionTabs
      .locator('[data-frame="sectionTabBadge"]')
      .first()
      .evaluate((item) => {
        const style = getComputedStyle(item);
        return [
          'borderTopLeftRadius',
          'borderTopRightRadius',
          'borderBottomRightRadius',
          'borderBottomLeftRadius'
        ].map((corner) => parseFloat(style[corner]));
      }),
    [15, 15, 15, 15]
  );
  await sectionTabs.getByRole('tab', { name: 'Section 1', exact: true }).tap();
  assert.equal(
    await page.evaluate(() => window.projectsHarness.sectionCalls),
    1
  );
  await page.mouse.move(20, 28);
  await page.waitForTimeout(150);
  await page.mouse.move(100, 28);
  await page.mouse.down();
  await page.mouse.move(100, 79, { steps: 8 });
  await page.mouse.up();
  assert.deepEqual(
    await page.evaluate(() =>
      window.projectsHarness.sections.map((tab) => tab.id)
    ),
    ['section1', 'section0', 'section2']
  );
  assert.deepEqual(
    await page.evaluate(() => window.projectsHarness.sectionReorders),
    [[0, 1]]
  );
  await page.mouse.move(20, 73);
  await page.waitForTimeout(150);
  await page.mouse.move(100, 73);
  await page.mouse.down();
  await page.mouse.move(100, 125, { steps: 8 });
  await page.keyboard.press('Escape');
  await page.mouse.up();
  assert.equal(
    await page.evaluate(() => window.projectsHarness.sectionReorders.length),
    1
  );
  await page.mouse.move(20, 73);
  await page
    .locator('.section-tab-reveal:popover-open')
    .getByRole('button', { name: 'Close tab', exact: true })
    .click();
  assert.equal(
    await page.evaluate(() => window.projectsHarness.sections.length),
    2
  );
  assert.equal(
    await page.evaluate(() => window.projectsHarness.sectionCalls),
    1
  );
  await page.mouse.move(20, 73);
  await page.mouse.click(20, 73, { button: 'right' });
  for (const name of ['Move section up', 'Move section down'])
    assert.equal(
      await page
        .getByRole('button', { name, exact: true })
        .evaluate((button) =>
          button.parentElement
            .querySelector('.app-icon')
            .classList.contains('icon-material-design')
        ),
      true,
      name
    );
  assert.equal(
    await page
      .getByRole('button', { name: 'Move section down', exact: true })
      .isDisabled(),
    true
  );
  await page
    .getByRole('button', { name: 'Move section up', exact: true })
    .click();
  assert.deepEqual(
    await page.evaluate(() => window.projectsHarness.sectionReorders.at(-1)),
    [1, 0]
  );
  await page.keyboard.press('Escape');
  await page.evaluate(async () => {
    await window.projectsHarness.configure('rail', 'md3', 'ru');
    window.projectsHarness.resetSections();
  });
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: 20, y: 118 }]
  });
  await page.waitForTimeout(550);
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchEnd',
    touchPoints: []
  });
  assert.equal(
    await page
      .getByRole('button', { name: 'Переместить раздел вниз', exact: true })
      .isDisabled(),
    true
  );
  assert.equal(
    await page.evaluate(() => window.projectsHarness.sectionCalls),
    0
  );
  await cdp.detach();
  await page.keyboard.press('Escape');
  await page.evaluate(
    () => (window.projectsHarness.sections[0].accent = 'white')
  );
  const namedBadge = await page
    .locator('.section-tab-row')
    .first()
    .locator('[data-frame="sectionTabBadge"]')
    .evaluate((node) => getComputedStyle(node).backgroundColor);
  assert.equal(namedBadge, 'rgb(189, 189, 189)');
  await page.mouse.move(20, 28);
  await page.evaluate(() =>
    window.projectsHarness.replaceSections(
      window.projectsHarness.sections.map((tab, index) => ({
        ...tab,
        title:
          index === 0
            ? 'Updated section with a long server-owned name '.repeat(6)
            : tab.title
      }))
    )
  );
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  const updated = page.locator('.section-tab-reveal:popover-open');
  assert(
    (await updated.getAttribute('aria-label')).startsWith('Updated section')
  );
  assert.equal((await updated.boundingBox()).width, 320);

  assert.deepEqual(errors, []);
  console.log(
    'Section rail first touch, middle drag, Escape, close, right click and long touch passed. Projects/tabs: first tap/click, filters, grouping, phone/inline, keyboard, reorder and close passed.'
  );
} finally {
  await browser?.close();
  await server.close();
}
