import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { exerciseUsers } from './frame_users.mjs';

const users = process.argv.includes('--users'),
  screen = users ? 'users' : 'groups';
const repo = fileURLToPath(new URL('../../', import.meta.url)),
  out = repo + 'tools/frame_' + screen + '/output/';
const native = JSON.parse(await readFile(out + 'qml.json', 'utf8'));
assert.equal(
  native.style,
  'Material',
  'Compare against the actual Handler control style'
);
const catalog = JSON.parse(await readFile(out + 'catalog.json', 'utf8'));
const cases = JSON.parse(
  await readFile(repo + 'tools/frame_' + screen + '/cases.json', 'utf8')
);
for (const [name, hash] of Object.entries(native.sha256))
  assert.equal(
    createHash('sha256')
      .update(await readFile(repo + 'src/tactic_stream/shared_ui/' + name))
      .digest('hex'),
    hash,
    'stale native capture: ' + name
  );
for (const [name, hash] of Object.entries(native.nativeSources))
  assert.equal(
    createHash('sha256')
      .update(await readFile('D:/grav/Tactic Stream/TH/' + name))
      .digest('hex'),
    hash,
    'stale native renderer: ' + name
  );
const server = await createServer({
  root: repo,
  configFile: false,
  resolve: {
    alias: {
      vue: repo + 'frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js'
    }
  },
  plugins: [vue()],
  logLevel: 'warn',
  server: {
    host: '127.0.0.1',
    port: 0,
    watch: {
      ignored: [
        '**/.tmp/**',
        '**/.venv/**',
        '**/.standalone*/**',
        '**/output/**'
      ]
    }
  }
});
await server.listen();
const url =
  'http://127.0.0.1:' +
  server.httpServer.address().port +
  '/tools/frame_' +
  screen +
  '/index.html';
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL,
  ignoreDefaultArgs: ['--hide-scrollbars']
});
let rectangles = 0,
  styles = 0,
  backgrounds = 0,
  interiors = 0;
const samples = [];
try {
  for (const mode of ['dark', 'light'])
    for (const language of ['en', 'ru'])
      for (const [width, height] of [
        [1100, 660],
        [800, 560],
        [360, 740]
      ]) {
        const page = await browser.newPage({ viewport: { width, height } }),
          errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.route('**/admin/security-' + screen + '/read', (route) =>
          route.fulfill({ json: { result: catalog } })
        );
        await page.goto(url + '?mode=' + mode + '&language=' + language);
        await page.waitForFunction(
          () =>
            window.frameGroups?.groups.value?.catalog &&
            !window.frameGroups.groups.value.busy
        );
        if (width !== 800)
          await page.evaluate(() => {
            const style = [
              ...document.querySelectorAll('style[data-vite-dev-id]')
            ].find((el) => el.dataset.viteDevId.endsWith('/frame/frame.css'));
            document.head.appendChild(style);
          });
        await page.evaluate(() => document.fonts.ready);
        for (const c of cases) {
          for (const event of c.actions) {
            const control = page.locator('[data-frame="' + event.id + '"]');
            if (event.type === 'click') await control.click();
            else if (event.type === 'text') await control.fill(event.value);
            else
              await page.evaluate((value) => {
                const group = window.frameGroups.groups.value;
                if (group.$el.classList.contains('security-users')) {
                  group.catalog.canWrite = value !== 'readonly';
                  group.uncertain = value === 'uncertain';
                  group.error = group.uncertain
                    ? 'The save result is unknown. Reload users before trying again.'
                    : '';
                  group.busy = value === 'busy';
                  return;
                }
                if (value === 'single-line') {
                  const user = group.catalog.users.find(
                    (user) => user.login === 'user_0'
                  );
                  user.displayName = user.login;
                  user.initials = 'U';
                  group.dispatch({ type: 'query', value: 'user_0' });
                  return;
                }
                group.uncertain = value === 'uncertain';
                group.error = group.uncertain
                  ? 'The save result is unknown. Reload groups before trying again.'
                  : '';
                group.busy = value === 'busy';
              }, event.value);
            await page.waitForTimeout(20);
          }
          await page.evaluate(() => document.activeElement.blur());
          await page.mouse.move(width - 1, height - 1);
          await page.waitForTimeout(25);
          const sample = await page.evaluate(() => {
            const group = window.frameGroups.groups.value,
              boxes = {},
              paint = {},
              backgrounds = {},
              canvas = document.createElement('canvas');
            canvas.width = canvas.height = 1;
            const ctx = canvas.getContext('2d');
            const color = (value) => {
              ctx.clearRect(0, 0, 1, 1);
              ctx.fillStyle = value;
              ctx.fillRect(0, 0, 1, 1);
              return (
                '#' +
                [...ctx.getImageData(0, 0, 1, 1).data]
                  .slice(0, 3)
                  .map((v) => v.toString(16).padStart(2, '0'))
                  .join('')
              );
            };
            for (const el of document.querySelectorAll('[data-frame]')) {
              const r = el.getBoundingClientRect();
              let visible = true;
              for (let p = el.parentElement; p; p = p.parentElement) {
                const css = getComputedStyle(p);
                if (
                  /hidden|auto|scroll/.test(
                    css.overflow + css.overflowX + css.overflowY
                  )
                ) {
                  const clip = p.getBoundingClientRect();
                  if (
                    r.bottom <= clip.top ||
                    r.top >= clip.bottom ||
                    r.right <= clip.left ||
                    r.left >= clip.right
                  ) {
                    visible = false;
                    break;
                  }
                }
              }
              if (!visible) continue;
              boxes[el.dataset.frame] = {
                x: r.x,
                y: r.y,
                width: r.width,
                height: r.height
              };
              const css = getComputedStyle(el);
              paint[el.dataset.frame] = {
                fontSize: parseFloat(css.fontSize),
                weight: Number(css.fontWeight),
                color: color(css.color)
              };
              const surface = el.matches('.frame-checkbox,.frame-action')
                ? el.querySelector(':scope > .item-surface')
                : el;
              ctx.clearRect(0, 0, 1, 1);
              ctx.fillStyle = getComputedStyle(surface).backgroundColor;
              ctx.fillRect(0, 0, 1, 1);
              backgrounds[el.dataset.frame] = [
                ...ctx.getImageData(0, 0, 1, 1).data
              ];
            }
            const user = group.$el.classList.contains('security-users');
            const state = user
              ? {
                  ui: JSON.parse(JSON.stringify(group.ui)),
                  dirty: group.dirty,
                  uncertain: group.uncertain,
                  draft: {
                    login: group.draft?.login || '',
                    first_name: group.draft?.first_name || '',
                    groups: group.draft?.groups || []
                  },
                  identity: group.identity
                }
              : {
                  ui: JSON.parse(JSON.stringify(group.ui)),
                  dirty: group.dirty,
                  uncertain: group.uncertain,
                  draft: {
                    code: group.draft?.code || '',
                    name: group.draft?.name || '',
                    description: group.draft?.description || ''
                  },
                  memberCount: group.members.length
                };
            return {
              scene: { toolbar: group.toolbarScene, body: group.frameScene },
              state,
              boxes,
              styles: paint,
              backgrounds
            };
          });
          const reference = native.captures.find(
            (r) =>
              r.mode === mode &&
              r.language === language &&
              r.width === width &&
              r.phase === c.phase
          );
          const label = [mode, language, width, c.phase].join(' ');
          assert.deepEqual(sample.state, reference.state, label + ' state');
          assert.deepEqual(sample.scene, reference.scene, label + ' graph');
          for (const [id, expected] of Object.entries(
            reference.interiors || {}
          )) {
            const el = page.locator('[data-frame="' + id + '"]');
            if (expected.icon || expected.indicator) {
              const actual = await el
                .locator(
                  expected.icon
                    ? ':scope > .app-icon'
                    : ':scope > .app-checkbox-indicator'
                )
                .boundingBox();
              assert(actual, label + ' missing interior ' + id);
              const box = expected.icon || expected.indicator;
              const text = el.locator(
                  ':scope > span:not(.app-icon,.app-button-badge)'
                ),
                textBox =
                  expected.icon && (await text.count())
                    ? await text.boundingBox()
                    : null;
              // Qt snaps glyph advances; Chromium uses fractional advances. Compare centered content with its measured text width.
              const shaped = textBox
                ? {
                    ...box,
                    x: box.x + (expected.labelWidth - textBox.width) / 2
                  }
                : box;
              for (const key of ['x', 'y', 'width', 'height'])
                assert(
                  Math.abs(actual[key] - shaped[key]) <= 0.6,
                  JSON.stringify({
                    label,
                    id,
                    key,
                    actual: actual[key],
                    expected: shaped[key]
                  })
                );
              if (textBox)
                assert.equal(
                  await el.evaluate((el) =>
                    parseFloat(getComputedStyle(el).gap)
                  ),
                  expected.spacing,
                  label + ' native content spacing'
                );
              if (expected.icon) {
                const outer = await el.boundingBox();
                assert(
                  actual.x >= outer.x &&
                    actual.x + actual.width <= outer.x + outer.width,
                  label + ' ' + id + ' icon fits'
                );
                const text = el.locator(
                  ':scope > span:not(.app-icon,.app-button-badge)'
                );
                if (await text.count()) {
                  const r = await text.boundingBox();
                  assert(
                    r.x >= outer.x && r.x + r.width <= outer.x + outer.width,
                    label + ' ' + id + ' full label fits'
                  );
                }
              }
              interiors++;
            }
            if (id.startsWith('groupDescription_')) {
              const actual = await el.locator(':scope > span').boundingBox(),
                outer = await el.boundingBox();
              assert(
                Math.abs(actual.height - expected.textHeight) <= 1,
                label + ' ' + id + ' text height'
              );
              assert(
                Math.abs(
                  actual.y -
                    (outer.y + (outer.height - expected.textHeight) / 2)
                ) <= 0.6,
                label + ' ' + id + ' text inset'
              );
              interiors++;
            }
          }
          for (const id of users
            ? ['adminUsersList', 'adminUserGroupsList', 'adminUserForm']
            : [
                'securityGroupsList',
                'securityMembersList',
                'securityGroupDetails'
              ]) {
            const view = page.locator('[data-frame="' + id + '"]');
            if (!(await view.count())) continue;
            const bar = await view.evaluate((el) => ({
              gutter: el.offsetWidth - el.clientWidth,
              overflow: el.scrollHeight > el.clientHeight,
              thumb: getComputedStyle(el, '::-webkit-scrollbar-thumb')
                .backgroundColor
            }));
            assert.equal(
              bar.gutter,
              12,
              label + ' ' + id + ' reserved scrollbar gutter'
            );
            if (bar.overflow) {
              assert.notEqual(
                bar.thumb,
                'rgba(0, 0, 0, 0)',
                label + ' ' + id + ' visible thumb'
              );
              interiors++;
            }
          }
          const clipped = await page
            .locator('.frame-button:not(.icon-button)')
            .evaluateAll((buttons) =>
              buttons.flatMap((button) => {
                const label = button.querySelector(
                  ':scope > span:not(.app-icon,.app-button-badge)'
                );
                if (!label) return [];
                const b = button.getBoundingClientRect(),
                  r = label.getBoundingClientRect();
                return r.x < b.x - 0.1 ||
                  r.right > b.right + 0.1 ||
                  r.y < b.y - 0.1 ||
                  r.bottom > b.bottom + 0.1
                  ? [button.dataset.frame]
                  : [];
              })
            );
          assert.deepEqual(
            clipped,
            [],
            label + ' button labels fit without wrapping or clipping'
          );
          for (const [id, box] of Object.entries(sample.boxes)) {
            const qml = reference.boxes[id];
            assert(qml, label + ' missing QML control ' + id);
            for (const key of ['x', 'y', 'width', 'height'])
              assert(
                Math.abs(box[key] - qml[key]) <= 0.08,
                JSON.stringify({ label, id, key, vue: box[key], qml: qml[key] })
              );
            rectangles++;
            if (reference.styles[id]?.color) {
              assert.deepEqual(
                sample.styles[id],
                reference.styles[id],
                label + ' ' + id + ' typography/color'
              );
              styles++;
            }
            if (reference.backgrounds[id]) {
              assert.deepEqual(
                sample.backgrounds[id],
                reference.backgrounds[id],
                label + ' ' + id + ' background'
              );
              backgrounds++;
            }
          }
          assert.equal(
            await page.evaluate(() => document.documentElement.scrollWidth),
            width,
            label + ' horizontal overflow'
          );
          const image =
            screen +
            '-vue-' +
            mode +
            '-' +
            language +
            '-' +
            width +
            '-' +
            c.phase +
            '.png';
          await page.screenshot({ path: out + image, animations: 'disabled' });
          samples.push({
            mode,
            language,
            width,
            height,
            phase: c.phase,
            image
          });
        }
        assert.deepEqual(errors, []);
        await page.close();
      }
  if (users) await exerciseUsers(browser, url, catalog);
  else {
    const context = await browser.newContext({
      viewport: { width: 360, height: 740 },
      hasTouch: true
    });
    const page = await context.newPage(),
      writes = [];
    let stored = structuredClone(catalog),
      reads = 0,
      reply = 'success';
    await page.route('**/admin/security-groups/*', async (route) => {
      if (route.request().url().endsWith('/read')) {
        reads++;
        await route.fulfill({ json: { result: stored } });
        return;
      }
      const payload = route.request().postDataJSON();
      writes.push(payload);
      if (reply === 'unknown') {
        await route.abort('failed');
        return;
      }
      if (reply === 'conflict') {
        await route.fulfill({
          status: 409,
          json: { error: 'Group details changed. Reload before saving.' }
        });
        return;
      }
      const code = payload.group_code || 'NEW_FRAME_GROUP';
      stored.groups = stored.groups.filter((row) => row.code !== code);
      stored.groups.push({
        code,
        name: payload.login_group,
        description: payload.description,
        revision: 'revision-after-save',
        memberCount: payload.add_members.length
      });
      stored.memberships.push(
        ...payload.add_members.map((login) => ({
          login,
          login_group: payload.login_group
        }))
      );
      await route.fulfill({ json: { result: { ...stored, selected: code } } });
    });
    await page.goto(url);
    const control = (id) => page.locator('[data-frame="' + id + '"]');
    const ready = () =>
      page.waitForFunction(() => !window.frameGroups.groups.value.busy);
    await control('createSecurityGroup').waitFor();
    await ready();
    await control('createSecurityGroup').tap();
    await control('securityGroupName').fill('touch_team');
    await control('securityGroupDescription').fill('Native and browser team');
    await control('segmentedButtonSegment_members').tap();
    await control('securityMemberSearch').fill('Participant 01');
    await control('securityMember_user_1').tap();
    assert.equal(writes.length, 0, 'Draft edits must not write on the server');
    await control('saveSecurityGroup').tap();
    await ready();
    assert.equal(writes.length, 1);
    assert.deepEqual(writes[0], {
      ticket: 'isolated-frame-test',
      project: 'sthpw',
      group_code: '',
      login_group: 'touch_team',
      description: 'Native and browser team',
      expected_revision: '',
      add_members: ['user_1'],
      remove_members: []
    });
    assert.equal(
      await control('securityGroupNotice').inputValue(),
      'Group saved on server'
    );
    await control('segmentedButtonSegment_details').tap();
    assert.equal(
      await control('securityGroupName').getAttribute('readonly'),
      ''
    );
    await control('securityGroupDescription').fill('Uncertain draft');
    reply = 'unknown';
    await control('saveSecurityGroup').tap();
    await ready();
    assert.equal(await control('saveSecurityGroup').isDisabled(), true);
    await page.evaluate(() => window.frameGroups.groups.value.save());
    assert.equal(writes.length, 2, 'An unknown result must not be retried');
    await control('adminReloadDocument').tap();
    assert.equal(reads, 1);
    await control('keepSecurityGroup').tap();
    assert.equal(
      await control('securityGroupDescription').inputValue(),
      'Uncertain draft'
    );
    await control('adminReloadDocument').tap();
    await control('confirmDiscardSecurityGroup').tap();
    await ready();
    assert.equal(reads, 2);
    assert.equal(
      await page.evaluate(() => window.frameGroups.groups.value.uncertain),
      false
    );
    await control('securityGroupDescription').fill('Stale draft');
    reply = 'conflict';
    await control('saveSecurityGroup').tap();
    await ready();
    assert.equal(writes.at(-1).expected_revision, 'revision-after-save');
    assert.equal(
      await control('securityGroupDescription').inputValue(),
      'Stale draft'
    );
    assert.equal(
      await page.evaluate(() => window.frameGroups.groups.value.canLeave()),
      false
    );
    await control('adminDiscardDocument').tap();
    await control('confirmDiscardSecurityGroup').tap();
    assert.equal(
      await control('securityGroupDescription').inputValue(),
      'Native and browser team'
    );
    await context.close();
  }
  await writeFile(
    out + 'vue.json',
    JSON.stringify(
      { captures: samples, rectangles, styles, backgrounds, interiors },
      null,
      2
    )
  );
  console.log(
    'PASS: ' +
      samples.length +
      ' paired production ' +
      screen +
      ' states; ' +
      rectangles +
      ' rectangles; ' +
      styles +
      ' text styles; ' +
      backgrounds +
      ' backgrounds; ' +
      interiors +
      ' interiors'
  );
} finally {
  await browser.close();
  await server.close();
}
