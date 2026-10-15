import assert from 'node:assert/strict';

export async function exerciseControls(page) {
  const control = (id) => page.locator(`[data-frame="${id}"]`).first();
  const configure = async (options) => {
    await page.evaluate(
      (options) => window.frameControls.configure(options),
      options
    );
    await page.evaluate(
      () => new Promise((resolve) => requestAnimationFrame(resolve))
    );
  };
  await page.setViewportSize({ width: 900, height: 900 });
  await configure({
    width: 900,
    height: 900,
    state: 'idle',
    mode: 'dark',
    theme: 'md3',
    language: 'en'
  });
  await page.evaluate(() => window.frameControls.reset());
  await control('iconButton').hover();
  await page.getByRole('tooltip', { name: 'Help', exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await page
    .getByRole('tooltip', { name: 'Help', exact: true })
    .waitFor({ state: 'hidden' });
  const menu = control('menu');
  await menu.locator('summary').press('ArrowDown');
  await page
    .getByRole('menuitem', { name: 'Save', exact: true })
    .press('Enter');
  assert.equal(
    await page.evaluate(
      () =>
        window.frameControls.model.events.filter(
          (event) => event.type === 'menu_0'
        ).length
    ),
    1
  );
  await menu.locator('summary').click();
  await menu.locator('.account-panel:popover-open').waitFor();
  await page.keyboard.press('Escape');
  assert.equal(
    await menu
      .locator('summary')
      .evaluate((element) => element === document.activeElement),
    true
  );
  await control('button').click();
  await control('button').press('Space');
  await control('button').tap();
  assert.equal(
    await page.evaluate(
      () =>
        window.frameControls.model.events.filter(
          (event) => event.type === 'save'
        ).length
    ),
    3,
    'One action for each mouse/key/touch activation'
  );
  await configure({ state: 'disabled' });
  const box = await control('button').boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  assert.equal(
    await page.evaluate(
      () =>
        window.frameControls.model.events.filter(
          (event) => event.type === 'save'
        ).length
    ),
    3
  );
  await configure({ state: 'readonly' });
  await control('field').click();
  await page.keyboard.press('End');
  await page.keyboard.type('ignored');
  assert.equal(await control('field').inputValue(), 'Robot Arm');
  await configure({ state: 'error' });
  assert.equal(await control('field').getAttribute('aria-invalid'), 'true');
  await configure({ state: 'idle' });
  await control('field').fill('Edited');
  await control('area').fill('First line\nSecond line');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.description),
    'First line\nSecond line'
  );
  assert.equal(
    await page.evaluate(() => window.frameControls.model.text),
    'Edited'
  );
  await control('check').getByRole('checkbox').click();
  assert.equal(
    await page.evaluate(() => window.frameControls.model.mixed),
    false
  );
  assert.equal(
    await page.evaluate(() => window.frameControls.model.checked),
    true,
    'Mixed activation checks the value in both engines'
  );
  assert.deepEqual(
    await page.evaluate(() =>
      window.frameControls.model.events.filter(
        (event) => event.type === 'checked'
      )
    ),
    [{ type: 'checked', value: true }]
  );
  await control('choice').selectOption('rig');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.choice),
    'rig'
  );
  const date = control('date');
  await date.getByLabel('Choose date and time', { exact: true }).click();
  await date.locator('.account-panel:popover-open').waitFor();
  await date.locator('[data-day="29"]').press('ArrowRight');
  await page.keyboard.press('Enter');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.date),
    '2024-03-01T13:14'
  );
  assert.equal(
    await page.evaluate(
      () =>
        window.frameControls.model.events.filter(
          (event) => event.type === 'dateCommit'
        ).length
    ),
    1
  );
  await date.getByRole('textbox').fill('0099-02-28T13:14');
  await date.getByLabel('Choose date and time', { exact: true }).click();
  await date
    .getByRole('button', { name: '28 February 99', exact: true })
    .click();
  assert.equal(
    await page.evaluate(() => window.frameControls.model.date),
    '0099-02-28T13:14'
  );
  const user = control('user');
  await user.locator('summary').click();
  const search = user.getByRole('combobox', {
    name: 'Search users',
    exact: true
  });
  await search.fill('test');
  await search.press('ArrowDown');
  await page.keyboard.press('Enter');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.user),
    'test'
  );
  await page.waitForFunction(
    () =>
      document
        .querySelector('[data-frame="user"] > summary')
        .getAttribute('aria-expanded') === 'false'
  );
  assert.equal(
    await user.locator('summary').getAttribute('aria-expanded'),
    'false'
  );
  await user.locator('summary').click();
  await user.locator('.account-panel:popover-open').waitFor();
  await configure({ state: 'disabled' });
  assert.equal(
    await user.locator('.account-panel:popover-open').count(),
    0,
    'A disabled owner closes its popup'
  );
  await configure({ state: 'idle' });
  const icon = control('icon');
  await icon.locator('summary').click();
  const library = icon.locator('.account-panel:popover-open');
  await library.waitFor();
  assert.equal(
    await page
      .getByRole('dialog', { name: 'Choose icon', exact: true })
      .count(),
    0,
    'Icon picker is an anchored panel'
  );
  assert.ok(
    (await library.locator('.icon-library button').count()) < 100,
    'Icon grid materializes visible rows only'
  );
  await library
    .getByRole('textbox', { name: 'Search icons', exact: true })
    .press('ArrowDown');
  await page.keyboard.press('ArrowRight');
  assert.equal(
    await library
      .locator('[data-icon-index="1"]')
      .evaluate((element) => element === document.activeElement),
    true
  );
  await page.keyboard.press('Home');
  assert.equal(
    await library
      .locator('[data-icon-index="0"]')
      .evaluate((element) => element === document.activeElement),
    true
  );
  await library
    .getByRole('textbox', { name: 'Search icons', exact: true })
    .fill('content-save');
  await library
    .getByRole('button', { name: 'content-save', exact: true })
    .click();
  assert.equal(
    await page.evaluate(() => window.frameControls.model.icon),
    'material-design:content-save'
  );
  assert.equal(await library.count(), 0);
  const color = control('color');
  await color.getByRole('button').click();
  const picker = page.getByRole('dialog', {
    name: 'Choose a color',
    exact: true
  });
  await picker
    .getByRole('textbox', { name: 'Color in HEX format', exact: true })
    .fill('#123456');
  await picker.getByRole('button', { name: 'Cancel', exact: true }).click();
  assert.equal(
    await page.evaluate(() => window.frameControls.model.color),
    '#78a6c4'
  );
  await page.evaluate(() => (window.frameControls.model.color = ''));
  await color.getByRole('button').click();
  assert.equal(
    await picker
      .getByRole('textbox', { name: 'Color in HEX format', exact: true })
      .inputValue(),
    '#78a6c4',
    'Empty colors start at the active accent'
  );
  await picker
    .getByRole('textbox', { name: 'Color in HEX format', exact: true })
    .fill('#123456');
  await picker.getByRole('button', { name: 'OK', exact: true }).click();
  assert.equal(
    await page.evaluate(() => window.frameControls.model.color),
    '#123456'
  );
  await color.getByRole('button').click();
  await picker.waitFor();
  await configure({ state: 'disabled' });
  await picker.waitFor({ state: 'hidden' });
  assert.equal(
    await page.evaluate(() => window.frameControls.model.color),
    '#123456'
  );
  await configure({ state: 'idle' });
  const tree = control('tree');
  await tree.scrollIntoViewIfNeeded();
  await control('tree_assets').focus();
  await page.keyboard.press('ArrowDown');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.treeSelected),
    'arm'
  );
  assert.equal(
    await control('tree_arm').evaluate(
      (element) => element === document.activeElement
    ),
    true
  );
  await page.keyboard.press('ArrowLeft');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.treeSelected),
    'assets'
  );
  await page.keyboard.press('ArrowLeft');
  assert.equal(
    await control('tree_assets').getAttribute('aria-expanded'),
    'false'
  );
  await page.keyboard.press('ArrowRight');
  assert.equal(
    await control('tree_assets').getAttribute('aria-expanded'),
    'true'
  );
  await control('splitter').scrollIntoViewIfNeeded();
  await control('splitter').press('End');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.split),
    100
  );
  await control('splitter').press('Home');
  assert.equal(await page.evaluate(() => window.frameControls.model.split), 0);
  const grid = control('grid');
  await grid.scrollIntoViewIfNeeded();
  await grid.locator('.frame-grid-body').evaluate((element) => {
    element.scrollTop = 1200;
    element.scrollLeft = 200;
  });
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(resolve))
  );
  assert.ok(
    (await grid.locator('[data-frame^="cell_"]').count()) < 100,
    'Table cells remain bounded by the viewport'
  );
  assert.ok((await grid.locator('[data-frame^="cell_3"]').count()) > 0);
  await configure({ width: 360, height: 900 });
  await page.setViewportSize({ width: 360, height: 900 });
  await control('splitter').scrollIntoViewIfNeeded();
  assert.equal(
    await control('splitter').isVisible(),
    true,
    'The owner controls splitter visibility on narrow layouts'
  );
  await control('splitter').press('End');
  assert.equal(
    await page.evaluate(() => window.frameControls.model.split),
    100
  );
  console.log(
    'Actual control mouse, touch, keyboard, draft, popup, tree and table input passed.'
  );
}
