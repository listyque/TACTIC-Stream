// Exercise the generated local report, not a second mock of its filtering code.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(
  new URL('../../frontend/package.json', import.meta.url)
);
const { chromium } = require('playwright');
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(new URL('output/ui-elements.html', import.meta.url).href);
  assert.equal(await page.locator('article').count(), 27);
  await page.locator('#family').selectOption('dates');
  assert.equal(await page.locator('article').count(), 1);
  await page
    .getByRole('button', { name: 'Все исходники и применения', exact: true })
    .click();
  assert((await page.locator('#total').textContent()).includes('записей'));
  await page.locator('#family').selectOption('');
  await page
    .getByRole('button', { name: 'Все компоненты и helpers', exact: true })
    .click();
  await page.locator('#engine').selectOption('native');
  await page.locator('#search').fill('ProjectFilterToggles');
  assert.equal(await page.locator('tbody tr').count(), 1);
  assert(
    (await page.locator('tbody tr').textContent()).includes(
      'Форма / предметный фрагмент'
    )
  );
  await page.locator('#search').fill('SettingRow');
  await page.locator('#engine').selectOption('vue');
  const setting = page.getByRole('link', { name: 'SettingRow', exact: true });
  assert.equal(await setting.count(), 1);
  assert(
    (await setting.locator('xpath=ancestor::tr').textContent()).includes(
      'Базовый составной'
    )
  );
  await page.locator('#search').fill('');
  await page.locator('#engine').selectOption('');
  await page
    .getByRole('button', { name: 'Все места использования', exact: true })
    .click();
  assert.equal(await page.locator('tbody tr').count(), 60);
  const first = await page.locator('tbody tr').first().textContent();
  await page.getByRole('button', { name: 'Далее', exact: true }).click();
  assert.notEqual(await page.locator('tbody tr').first().textContent(), first);
  await page
    .getByRole('button', { name: 'Семейства и варианты', exact: true })
    .click();
  assert.equal(await page.locator('article').count(), 27);
  assert(await page.locator('#pages').isHidden());
  await page.locator('article').last().scrollIntoViewIfNeeded();
  await page.waitForFunction(() =>
    [...document.images].every((image) => image.complete)
  );
  assert.deepEqual(
    await page
      .locator('img')
      .evaluateAll((images) =>
        images.filter((image) => !image.naturalWidth).map((image) => image.src)
      ),
    []
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#family').selectOption('buttons');
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth
    )
  );
  await page.screenshot({
    path: fileURLToPath(new URL('output/atlas-mobile.png', import.meta.url)),
    fullPage: true
  });
  assert.deepEqual(errors, []);
  console.log(
    'UI atlas: families, source classification, filters, paging and real image crops passed.'
  );
} finally {
  await browser.close();
}
