import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const base = process.argv[2],
  project = process.env.STREAM_CHECK_PROJECT;
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    hasTouch: true,
    colorScheme: 'dark'
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.clock.install();
  await page.route('http://tactic-stream.test/**', async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      response: await route.fetch({
        url: base + url.pathname + url.search,
        headers: {
          ...route.request().headers(),
          origin: base,
          referer: base + '/'
        }
      })
    });
  });
  const record = (index) => ({
    eventId: `note:PAGING_${index}`,
    kind: 'note',
    actor: 'artist',
    actorLabel: 'Artist',
    title: `Paging event ${index}`,
    detail: `Event number ${index}`,
    targetTitle: 'Episode',
    timestamp: `2026-10-01 12:${String(Math.floor(index / 60)).padStart(2, '0')}:${String(index % 60).padStart(2, '0')}`,
    dayKey: '2026-10-01'
  });
  let rows = Array.from({ length: 180 }, (_, index) => record(179 - index)),
    failure = false,
    held = null,
    holdOffset = -1;
  const calls = [],
    active = new Set();
  await page.route(
    'http://tactic-stream.test/admin/server-updates',
    (route) => {
      const after = route.request().postDataJSON().activity_after || '';
      const activity = rows
        .filter((row) => row.timestamp > after)
        .map((row) => ({
          __kind__: 'note',
          __event_timestamp__: row.timestamp
        }));
      return route.fulfill({
        json: {
          result: {
            activity,
            messages: [],
            reactions: [],
            presence: [],
            cacheChanges: [],
            cacheRetired: []
          }
        }
      });
    }
  );
  await page.route(
    'http://tactic-stream.test/admin/activity-feed',
    async (route) => {
      const values = route.request().postDataJSON(),
        start = values.offset || 0;
      calls.push({ ...values, offset: start });
      if (values.counts_only)
        return route.fulfill({
          json: { result: { records: [], dayCounts: [], users: [] } }
        });
      assert(!active.has(start), `Concurrent page ${start}`);
      active.add(start);
      try {
        if (start === holdOffset)
          await new Promise((resolve) => {
            held = resolve;
          });
        if (failure)
          return await route.fulfill({
            status: 500,
            json: { error: { message: 'Paging failed' } }
          });
        const records = rows.slice(start, start + 25);
        await route.fulfill({
          json: {
            result: {
              records,
              hasMore: start + records.length < rows.length,
              nextOffset: start + records.length,
              users: [],
              dayCounts: []
            }
          }
        });
      } finally {
        active.delete(start);
      }
    }
  );
  await page.goto('http://tactic-stream.test/');
  await page
    .getByLabel('Login', { exact: true })
    .fill(process.env.STREAM_CHECK_LOGIN || 'admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.project-picker').waitFor();
  await selectProject(page, project);
  await page.locator('.activity-feed-trigger').click();
  const dialog = page.getByRole('dialog', {
      name: 'Activity Feed',
      exact: true
    }),
    viewport = dialog.locator('.activity-feed-events');
  const count = async (size) => {
    try {
      await page.waitForFunction(
        (size) =>
          document.querySelectorAll(
            '.activity-feed-dialog .activity-event-card'
          ).length === size &&
          document
            .querySelector('.activity-feed-dialog')
            .getAttribute('aria-busy') === 'false',
        size
      );
    } catch (error) {
      console.error({
        expected: size,
        offsets: calls.map((call) => call.offset),
        state: await viewport.evaluate((element) => ({
          count: element.querySelectorAll('[data-event-id]').length,
          top: element.scrollTop,
          height: element.clientHeight,
          content: element.scrollHeight,
          busy: element.closest('dialog').getAttribute('aria-busy'),
          focus: document.activeElement.className
        }))
      });
      throw error;
    }
  };
  const ids = () =>
    dialog
      .locator('.activity-event-card')
      .evaluateAll((elements) =>
        elements.map((element) => element.dataset.eventId)
      );
  const bottom = () =>
    viewport.evaluate((element) => {
      element.scrollTop = element.scrollHeight;
    });
  const wheel = async () => {
    await viewport.hover();
    await viewport.evaluate((element) => {
      element.dataset.wheelDelivered = 'false';
      element.addEventListener(
        'wheel',
        () => {
          element.dataset.wheelDelivered = 'true';
        },
        { once: true }
      );
    });
    await page.mouse.wheel(0, 300);
    await page.waitForFunction(
      () =>
        document.querySelector('.activity-feed-dialog .activity-feed-events')
          .dataset.wheelDelivered === 'true'
    );
    await page.clock.runFor(50);
  };
  await count(25);
  assert.equal(
    await dialog
      .getByRole('button', { name: 'Load more activity', exact: true })
      .count(),
    0
  );

  // Position changes and thumb navigation never acquire a pagination permit.
  let before = calls.length;
  await bottom();
  await page.clock.runFor(100);
  assert.equal(calls.length, before);
  await viewport.evaluate((element) => {
    const box = element.getBoundingClientRect();
    document.dispatchEvent(
      new PointerEvent('pointerdown', {
        pointerId: 7,
        clientX: box.right - 1,
        clientY: box.top + 40,
        bubbles: true
      })
    );
  });
  await wheel();
  assert.equal(calls.length, before);
  await page.evaluate(() =>
    document.dispatchEvent(
      new PointerEvent('pointerup', { pointerId: 7, bubbles: true })
    )
  );
  await page.clock.runFor(100);
  assert.equal(calls.length, before);
  await wheel();
  await count(50);
  assert.equal(calls.at(-1).offset, 25);
  assert.equal(calls.length, before + 1);
  await page.clock.runFor(100);
  assert.equal(calls.length, before + 1);

  await bottom();
  await viewport.focus();
  await page.keyboard.press('End');
  await page.clock.runFor(50);
  await count(75);
  assert.equal(new Set(await ids()).size, 75);

  // Resizing a retained window fills its newly available height without a gesture.
  before = calls.length;
  await viewport.evaluate((element) => {
    element.scrollTop = 0;
  });
  await page.setViewportSize({ width: 1440, height: 15000 });
  await page.clock.runFor(100);
  await page.waitForFunction(
    () =>
      document.querySelectorAll('.activity-feed-dialog .activity-event-card')
        .length > 75
  );
  await page.waitForFunction(
    () =>
      document
        .querySelector('.activity-feed-dialog')
        .getAttribute('aria-busy') === 'false'
  );
  assert(calls.length > before);
  assert.deepEqual(
    calls.slice(before).map((call) => call.offset),
    Array.from({ length: calls.length - before }, (_, index) => 75 + index * 25)
  );
  assert.equal(new Set(await ids()).size, (await ids()).length);
  await page.setViewportSize({ width: 1440, height: 1000 });

  // Reconcile a burst across several pages and keep the same visible event at the same pixel.
  await dialog
    .getByRole('button', { name: 'Refresh activity', exact: true })
    .click();
  await count(25);
  await bottom();
  await wheel();
  await count(50);
  await viewport.evaluate((element) => {
    element.scrollTop = 1200;
  });
  const anchor = await viewport.evaluate((element) => {
    const item = [...element.querySelectorAll('[data-event-id]')].find(
      (item) =>
        item.getBoundingClientRect().bottom >
        element.getBoundingClientRect().top + 34
    );
    return { id: item.dataset.eventId, top: item.getBoundingClientRect().top };
  });
  rows = Array.from({ length: 40 }, (_, index) => ({
    ...record(219 - index),
    timestamp: `2099-01-01 12:00:${String(59 - index).padStart(2, '0')}`
  })).concat(rows);
  await page.clock.runFor(30000);
  await count(100);
  assert.deepEqual(
    await ids(),
    rows.slice(0, 100).map((row) => row.eventId)
  );
  const top = await viewport
    .locator(`[data-event-id="${anchor.id}"]`)
    .evaluate((element) => element.getBoundingClientRect().top);
  assert(Math.abs(top - anchor.top) < 1, `Anchor moved ${top - anchor.top}px`);
  await bottom();
  await wheel();
  await count(125);
  assert.deepEqual(
    await ids(),
    rows.slice(0, 125).map((row) => row.eventId)
  );

  // A rejected next page retains loaded events and does not retry in a loop.
  failure = true;
  before = calls.length;
  await bottom();
  await wheel();
  await dialog.locator('p.error[role=alert]').waitFor();
  await page.clock.runFor(1000);
  assert.equal(calls.length, before + 1);
  assert.equal((await ids()).length, 125);
  failure = false;
  await dialog.getByRole('button', { name: 'Retry', exact: true }).click();
  await count(25);

  // Filtering a short list continues through older pages, including a match on the last one.
  rows.at(-1).detail = 'Oldest hidden needle';
  before = calls.length;
  await dialog
    .getByLabel('Search activity', { exact: true })
    .fill('oldest hidden needle');
  await count(1);
  assert.equal((await ids())[0], rows.at(-1).eventId);
  assert.deepEqual(
    calls.slice(before).map((call) => call.offset),
    [25, 50, 75, 100, 125, 150, 175, 200]
  );
  await dialog.getByLabel('Search activity', { exact: true }).fill('');
  await dialog
    .getByRole('button', { name: 'Refresh activity', exact: true })
    .click();
  await count(25);

  // Polling during an in-flight page defers reconciliation rather than losing the update.
  holdOffset = 25;
  await bottom();
  await wheel();
  for (let attempt = 0; !held && attempt < 1200; attempt++)
    await new Promise((resolve) => setTimeout(resolve, 10));
  assert(held, 'Next-page request was not held');
  rows.unshift({ ...record(220), timestamp: '2099-01-02 12:00:00' });
  await page.clock.runFor(30000);
  await page.waitForFunction(
    () =>
      document
        .querySelector('.activity-feed-dialog')
        .getAttribute('aria-busy') === 'true'
  );
  holdOffset = -1;
  held();
  held = null;
  await count(50);
  assert.deepEqual(
    await ids(),
    rows.slice(0, 50).map((row) => row.eventId)
  );
  await dialog
    .getByRole('button', { name: 'Refresh activity', exact: true })
    .click();
  await count(25);

  // A delayed old page cannot append to a newer filter.
  holdOffset = 25;
  await bottom();
  await wheel();
  await page.waitForFunction(
    () =>
      document
        .querySelector('.activity-feed-dialog')
        .getAttribute('aria-busy') === 'true'
  );
  for (let attempt = 0; !held && attempt < 1200; attempt++)
    await new Promise((resolve) => setTimeout(resolve, 10));
  assert(held, 'Next-page request was not held');
  await dialog.getByRole('radio', { name: 'Notes', exact: true }).click();
  await count(25);
  holdOffset = -1;
  held();
  held = null;
  await page.clock.runFor(100);
  await count(25);
  assert.equal(
    await dialog
      .getByRole('radio', { name: 'Notes', exact: true })
      .getAttribute('aria-checked'),
    'true'
  );

  // Touch movement has the same permit; the screen stays usable at 320px.
  await page.setViewportSize({ width: 320, height: 760 });
  await page.clock.runFor(100);
  await bottom();
  await page.clock.runFor(50);
  before = calls.length;
  await viewport.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    const box = element.getBoundingClientRect();
    element.dispatchEvent(
      new PointerEvent('pointerdown', {
        pointerId: 9,
        pointerType: 'touch',
        clientX: box.left + 30,
        clientY: box.top + 60,
        bubbles: true
      })
    );
    element.dispatchEvent(new Event('scroll'));
    element.dispatchEvent(
      new PointerEvent('pointerup', {
        pointerId: 9,
        pointerType: 'touch',
        bubbles: true
      })
    );
  });
  await count(50);
  assert.equal(calls.length, before + 1);
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  );
  await dialog
    .getByRole('button', { name: 'Close Activity Feed', exact: true })
    .tap();
  before = calls.length;
  await page.setViewportSize({ width: 1440, height: 15000 });
  await page.clock.runFor(100);
  assert.equal(
    calls.length,
    before,
    'A hidden feed must not fill the resized viewport'
  );
  assert.deepEqual(errors, []);
  console.log(
    'Activity paging: native permits, auto fill/resize, burst continuity, stable anchor, errors, stale responses and touch320 PASS'
  );
} finally {
  await browser.close();
}
