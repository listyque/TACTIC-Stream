import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 }
  });
  page.setDefaultTimeout(15000);
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ language: 'en', mode: 'dark' })
    )
  );
  await page.goto(
    process.argv[2] + '/projects/one/?search_type=contract/entity&view=table'
  );
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page
    .locator('.handler-table-row:visible, .result-item:visible')
    .first()
    .waitFor();
  await page.getByLabel('Workspace panels', { exact: true }).click();
  await page
    .locator('.dock-menu summary[aria-label="Tasks and reports"]')
    .click();
  await page
    .locator('.dock-menu')
    .getByRole('menuitemradio', { name: 'Task Calendar', exact: true })
    .click();
  const calendar = page.locator('.task-calendar-view:visible');
  await calendar.waitFor();
  await calendar.locator('.task-calendar-day').first().waitFor();
  await page
    .locator('[data-dock="task_calendar"] [data-dock-control="dockMaximize"]')
    .click();
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 820, height: 1400 },
    { width: 360, height: 760 }
  ]) {
    await page.setViewportSize(viewport);
    await page.waitForFunction(() => {
      const root = document.querySelector('.task-calendar-view');
      const days = [...root.querySelectorAll('.task-calendar-day')];
      if (days.length !== 42) return false;
      const bounds = root.getBoundingClientRect();
      const first = days[0].getBoundingClientRect(),
        last = days[41].getBoundingClientRect();
      const surface = days[0]
        .querySelector('[data-frame="calendarDaySurface"]')
        .getBoundingClientRect();
      return (
        last.right <= bounds.right &&
        last.bottom <= bounds.bottom &&
        Math.abs(surface.width - first.width) < 1 &&
        Math.abs(surface.height - first.height) < 1
      );
    });
    const cells = await calendar
      .locator('.task-calendar-day')
      .evaluateAll((days) =>
        days.map((el) => el.getBoundingClientRect().toJSON())
      );
    for (let index = 1; index < 7; index++)
      assert(Math.abs(cells[index].left - cells[index - 1].right) <= 4.1);
    for (let index = 7; index < 42; index++)
      assert(Math.abs(cells[index].top - cells[index - 7].bottom) <= 4.1);
  }
  await page.setViewportSize({ width: 820, height: 1400 });
  const firstDate = await calendar
    .locator('.task-calendar-day')
    .first()
    .getAttribute('data-date');
  await calendar.locator('[data-frame="calendarNext"]').click();
  await page.waitForFunction(
    (date) =>
      document.querySelector('.task-calendar-day')?.dataset.date !== date,
    firstDate
  );
  await calendar.locator('[data-frame="calendarPrevious"]').click();
  await page.waitForFunction(
    (date) =>
      document.querySelector('.task-calendar-day')?.dataset.date === date,
    firstDate
  );
  await calendar.locator('[data-frame="calendarDayAction"]').nth(10).click();
  await calendar.locator('[data-frame="calendarClearDay"]').waitFor();
  await calendar.locator('[data-frame="calendarClearDay"]').click();
  await calendar.locator('[data-frame="calendarAgenda"]').click();
  assert(await calendar.locator('.task-calendar-agenda').isVisible());
  await calendar.locator('[data-frame="calendarAgenda"]').click();
  assert(await calendar.locator('.task-calendar-grid').isVisible());
  console.log('PASS calendar layout');
} finally {
  await browser.close();
}
