import assert from 'node:assert/strict';

// Test the rendered controls through their normal input paths, never call their reducers.
export async function exerciseVariants(page) {
  const sample = () => page.locator('[data-frame="sample"]');
  const model = () => page.evaluate(() => window.controlVariants.model);
  const configure = async (id, state = 'idle') => {
    await page.keyboard.press('Escape');
    await page.evaluate(
      (options) => window.controlVariants.configure(options),
      { id, state, width: 360 }
    );
    await page.evaluate(() => new Promise(requestAnimationFrame));
  };
  const state = async (value) => {
    await page.evaluate(
      (value) => window.controlVariants.setState(value),
      value
    );
    await page.evaluate(() => new Promise(requestAnimationFrame));
  };
  const clickEvenIfDisabled = async (element) => {
    const box = await element.boundingBox();
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  };

  await configure('button');
  await sample().click();
  await sample().press('Space');
  await sample().tap();
  assert.equal(
    (await model()).events.length,
    3,
    'One action per mouse, key and touch activation'
  );
  await state('disabled');
  await clickEvenIfDisabled(sample());
  assert.equal((await model()).events.length, 3);

  await configure('segments-disabled-option');
  const radios = sample().getByRole('radio');
  await radios.first().focus();
  await page.keyboard.press('ArrowRight');
  assert.equal((await model()).value, 'publish');
  await page.keyboard.press('ArrowRight');
  assert.equal((await model()).value, 'model');
  await page.keyboard.press('End');
  assert.equal((await model()).value, 'publish');
  await page.keyboard.press('Home');
  assert.equal((await model()).value, 'model');
  assert.equal((await model()).events.length, 4);
  assert.equal(await radios.nth(1).isDisabled(), true);
  assert.equal(
    await sample().locator('[role="radio"][tabindex="0"]').count(),
    1
  );
  await page.evaluate(() =>
    window.controlVariants.setAppearance({ language: 'ru' })
  );
  assert.equal(
    await radios.first().getAttribute('aria-label'),
    'Enabled',
    'Data labels are never translated'
  );

  await configure('date');
  assert.equal(await sample().getByRole('textbox').inputValue(), '2024-02-29');
  assert.equal(
    await sample().locator('.app-date-presentation').textContent(),
    '29 February 2024'
  );
  await configure('date-early-year');
  await page.evaluate(() =>
    window.controlVariants.setAppearance({ language: 'ru' })
  );
  assert.equal(
    await sample().locator('.app-date-presentation').textContent(),
    '1 января 0099'
  );
  await configure('date-invalid');
  assert.equal(
    await sample().getByRole('textbox').getAttribute('aria-invalid'),
    'true'
  );
  await configure('list-item');
  assert.equal(await sample().locator('.item-surface-rail').count(), 0);
  await configure('header');
  assert.equal(
    await sample().evaluate(
      (root) => getComputedStyle(root).borderTopLeftRadius
    ),
    '0px'
  );

  await configure('integer');
  const number = sample().getByRole('spinbutton');
  await number.focus();
  await page.keyboard.press('ArrowUp');
  assert.equal((await model()).value, 6);
  await number.fill('9');
  await number.press('Enter');
  await number.blur();
  assert.equal((await model()).value, 9);
  assert.equal(
    (await model()).events.length,
    2,
    'Enter followed by blur does not duplicate a commit'
  );
  await number.focus();
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('ArrowUp');
  assert.equal((await model()).value, 10);
  assert.equal(
    (await model()).events.length,
    3,
    'Stepping past the boundary emits nothing'
  );
  await state('readonly');
  await page.keyboard.press('ArrowDown');
  assert.equal((await model()).value, 10);
  assert.equal(await number.getAttribute('readonly'), '');
  await configure('decimal');
  await sample().getByRole('spinbutton').fill('2.5');
  await sample().getByRole('spinbutton').press('Enter');
  assert.equal((await model()).value, 2.5);

  await configure('slider-step');
  const slider = sample().getByRole('slider');
  const box = await slider.boundingBox();
  await page.mouse.click(box.x + box.width * 0.8, box.y + box.height / 2);
  assert((await model()).value > 50);
  assert.equal((await model()).value % 5, 0);
  const before = await model();
  await state('disabled');
  await clickEvenIfDisabled(slider);
  assert.deepEqual(await model(), before);
  await configure('slider-fixed');
  await clickEvenIfDisabled(sample().getByRole('slider'));
  assert.equal((await model()).value, 5);

  await configure('search-suggestions');
  let search = sample().getByRole('combobox');
  await search.focus();
  await sample().locator('.search-suggestions:popover-open').waitFor();
  await search.press('ArrowDown');
  await search.press('Enter');
  assert.equal((await model()).value, 'Robot Arm');
  assert.equal((await model()).events.length, 1);
  assert.equal(
    await sample().locator('.search-suggestions:popover-open').count(),
    0
  );
  await sample()
    .getByRole('button', { name: 'Clear search', exact: true })
    .click();
  assert.equal((await model()).value, '');
  await search.press('Escape');
  assert.equal((await model()).events.at(-1).type, 'dismiss');
  await configure('search-suggestions');
  search = sample().getByRole('combobox');
  await search.focus();
  await sample().locator('.search-suggestions:popover-open').waitFor();
  const searchBefore = await model();
  await state('disabled');
  assert.equal(
    await sample().locator('.search-suggestions:popover-open').count(),
    0
  );
  assert.deepEqual(await model(), searchBefore);

  await configure('choice-disabled-option');
  await sample().focus();
  await sample().selectOption('publish');
  assert.equal((await model()).value, 'publish');
  assert.equal(
    await sample().locator('option[value="rig"]').isDisabled(),
    true
  );

  await configure('checkbox-mixed');
  await sample().getByRole('checkbox').click();
  assert.equal((await model()).value, true);
  assert.equal((await model()).events.length, 1);
  assert.equal(
    await sample()
      .getByRole('checkbox')
      .evaluate((input) => input.indeterminate),
    false
  );

  await configure('users-multiple');
  await sample()
    .getByRole('checkbox', { name: 'Test Artist', exact: true })
    .click();
  assert.deepEqual((await model()).value, ['admin', 'test']);
  await sample()
    .getByRole('combobox', { name: 'Search users', exact: true })
    .fill('admin');
  assert.equal(await sample().getByRole('checkbox').count(), 1);
  assert.deepEqual(
    (await model()).value,
    ['admin', 'test'],
    'Filtering keeps the hidden selection'
  );

  await configure('accent-presets');
  await sample().getByRole('button', { name: 'Green', exact: true }).click();
  assert.equal((await model()).value, 'green');
  await state('disabled');
  await clickEvenIfDisabled(
    sample().getByRole('button', { name: 'Blue', exact: true })
  );
  assert.equal((await model()).value, 'green');

  await configure('menu-checks');
  await sample().locator('summary').click();
  await sample()
    .getByRole('menuitemradio', { name: 'Enabled', exact: true })
    .click();
  assert.equal((await model()).value, true);
  assert.equal(
    await sample().locator('.account-panel:popover-open').count(),
    0
  );
  await sample().locator('summary').focus();
  await sample().locator('summary').press('ArrowDown');
  await page.keyboard.press('Escape');
  assert.equal(
    await sample()
      .locator('summary')
      .evaluate((element) => element === document.activeElement),
    true
  );

  await configure('button-disclosure');
  await sample().getByRole('button').press('Space');
  assert.equal((await model()).value, true);
  await configure('button-preview');
  await sample().getByRole('button').press('Enter');
  assert.equal((await model()).events.length, 1);
  await configure('error-retry');
  await sample()
    .getByRole('button', { name: 'Retry', exact: true })
    .press('Space');
  assert.equal((await model()).events.at(-1).type, 'retry');

  await configure('emoji');
  await sample().locator('summary').click();
  await sample().locator('.emoji-grid button').first().waitFor();
  await sample().locator('.emoji-grid button').first().click();
  assert((await model()).value.length > 0);

  await configure('image-picker');
  const file = sample().locator('input[type=file]');
  await file.setInputFiles({
    name: 'unreadable.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not an image')
  });
  await sample().getByRole('alert').waitFor();
  assert.equal(
    (await model()).events.length,
    0,
    'Unreadable images never become a selected file'
  );
  await file.setInputFiles({
    name: 'example.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jv1sAAAAASUVORK5CYII=',
      'base64'
    )
  });
  await sample()
    .getByRole('button', { name: 'Undo image selection', exact: true })
    .waitFor();
  assert.equal((await model()).value, 'example.png');
  await sample()
    .getByRole('button', { name: 'Undo image selection', exact: true })
    .click();
  assert.equal((await model()).value, '');

  await configure('table');
  const cell = sample().locator('input').first();
  await cell.fill('Edited cell');
  assert(Object.values((await model()).cells).includes('Edited cell'));
  await page.evaluate(() => window.controlVariants.resize(900));
  assert(Object.values((await model()).cells).includes('Edited cell'));
  await configure('table-readonly');
  assert.equal(
    await sample().locator('input').first().getAttribute('readonly'),
    ''
  );

  await configure('packed-choices');
  const packed = sample().locator('[data-option-index]');
  assert(
    (await packed.count()) < 60,
    'Only visible chip rows are instantiated'
  );
  await packed.nth(1).click();
  assert.equal((await model()).value, '1');
  await sample()
    .locator('.example-options-viewport')
    .hover({ position: { x: 20, y: 20 } });
  await page.mouse.wheel(0, 1600);
  await page
    .waitForFunction(
      () =>
        Number(
          document.querySelector('[data-option-index]')?.dataset.optionIndex
        ) > 20
    )
    .catch(async (error) => {
      throw Error(
        error.message +
          ' ' +
          JSON.stringify(
            await sample().evaluate((root) =>
              [...root.querySelectorAll('*')]
                .filter(
                  (element) => element.scrollHeight > element.clientHeight
                )
                .map((element) => ({
                  class: element.className,
                  top: element.scrollTop,
                  client: element.clientHeight,
                  extent: element.scrollHeight
                }))
            )
          )
      );
    });
  assert.equal((await model()).value, '1');

  await configure('scroll-both');
  await sample().hover();
  await page.mouse.wheel(200, 200);
  await page.waitForFunction(() => {
    const element = document.querySelector('[data-frame="sample"]');
    return element.scrollTop > 0 && element.scrollLeft > 0;
  });
  await configure('splitter-vertical');
  await sample().press('ArrowRight');
  assert((await model()).value > 50);

  await configure('code');
  await sample()
    .getByRole('textbox', { name: 'Script source', exact: true })
    .fill('print("edited")\n');
  assert.equal((await model()).value, 'print("edited")\n');
  await page.evaluate(() => window.controlVariants.resize(900));
  assert.equal(
    await sample()
      .getByRole('textbox', { name: 'Script source', exact: true })
      .inputValue(),
    'print("edited")\n'
  );
  await configure('code-readonly');
  assert.equal(
    await sample()
      .getByRole('textbox', { name: 'Script source', exact: true })
      .isEditable(),
    false
  );

  await configure('graph');
  const graphNode = sample().locator('[data-frame="graphNode_a"]');
  await graphNode.click();
  assert.deepEqual((await model()).graphSelected, ['a']);
  const graphBox = await graphNode.boundingBox();
  await page.mouse.move(
    graphBox.x + graphBox.width / 2,
    graphBox.y + graphBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    graphBox.x + graphBox.width / 2 + 30,
    graphBox.y + graphBox.height / 2 + 20,
    { steps: 5 }
  );
  await page.mouse.up();
  assert(
    (await model()).graphPositions.some(
      (position) => position.identity === 'a' && position.nodeX !== 20
    )
  );

  for (const style of ['md3', 'material5', 'fluent']) {
    for (const id of [
      'button-badge',
      'button-disclosure',
      'button-send',
      'integer',
      'decimal',
      'date',
      'emoji',
      'tab',
      'tab-current',
      'menu',
      'menu-checks'
    ]) {
      await page.evaluate(
        (options) => window.controlVariants.configure(options),
        { id, style }
      );
      const sizes = await sample().evaluate((root) => {
        const parent = root.getBoundingClientRect(),
          child = root.firstElementChild.getBoundingClientRect();
        return {
          parent: { width: parent.width, height: parent.height },
          child: { width: child.width, height: child.height }
        };
      });
      assert.deepEqual(
        sizes.child,
        sizes.parent,
        `${style} ${id}: adapter respects shared geometry`
      );
      if (['integer', 'decimal', 'date'].includes(id)) {
        const field = await sample().locator('input').first().boundingBox();
        assert.equal(
          field.height,
          sizes.parent.height,
          `${style} ${id}: editor fills its assigned height`
        );
      }
      if (['emoji', 'menu', 'menu-checks'].includes(id)) {
        const trigger = await sample().locator('summary').first().boundingBox();
        assert.equal(trigger.width, sizes.parent.height);
        assert.equal(trigger.height, sizes.parent.height);
      }
    }
    await page.evaluate(
      (options) => window.controlVariants.configure(options),
      { id: 'users-multiple', style }
    );
    const searchHeight = await sample()
      .locator('.app-search-field')
      .evaluate((field) => [
        field.getBoundingClientRect().height,
        parseFloat(getComputedStyle(field).getPropertyValue('--control-height'))
      ]);
    assert.equal(
      searchHeight[0],
      searchHeight[1],
      `${style}: user search uses native theme height`
    );
    for (const mode of ['dark', 'light']) {
      await page.evaluate(
        (options) => window.controlVariants.configure(options),
        { id: 'search', style, mode }
      );
      for (const state of ['idle', 'focus', 'disabled']) {
        if (state === 'focus') await sample().getByRole('combobox').focus();
        if (state === 'disabled')
          await page.evaluate(() =>
            window.controlVariants.setState('disabled')
          );
        const colors = await sample()
          .locator('.app-search-field')
          .evaluate((field, state) => {
            const css = getComputedStyle(field),
              context = document.createElement('canvas').getContext('2d');
            const pixel = (color) => {
              context.fillStyle = color;
              context.fillRect(0, 0, 1, 1);
              return [...context.getImageData(0, 0, 1, 1).data];
            };
            return [
              {
                background: pixel(css.backgroundColor),
                border: pixel(css.borderLeftColor),
                width: parseFloat(css.borderLeftWidth)
              },
              {
                background: pixel(
                  css.getPropertyValue(`--field-${state}-background`)
                ),
                border: pixel(css.getPropertyValue(`--field-${state}-border`)),
                width: parseFloat(
                  css.getPropertyValue(`--field-${state}-border-width`)
                )
              }
            ];
          }, state);
        assert.deepEqual(
          colors[0],
          colors[1],
          `${style} ${mode} ${state}: shared search background and border`
        );
      }
    }
  }
  await page.setViewportSize({ width: 900, height: 520 });
  await page.evaluate(() =>
    window.controlVariants.configure({ id: 'image-picker', width: 900 })
  );
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  const chooseImage = await sample()
    .getByRole('button', { name: 'Choose image', exact: true })
    .boundingBox();
  // Current native EN fixture at 900 px places this button at x=419.
  assert(
    Math.abs(chooseImage.x - 419) < 1,
    'Image actions retain native proportional column placement'
  );
  await page.setViewportSize({ width: 360, height: 520 });
  await configure('button');
  console.log(
    'PASS expanded controls: real input, choice virtualization, two-axis scrolling, splitter, Grid drafts, Code edits and Graph select/move, plus fields/pickers/actions'
  );
}
