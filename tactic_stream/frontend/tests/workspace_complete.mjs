import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';
import { projectTree } from '../src/features/workspace/docks.js';

function assertDescriptionBelowResults(layout) {
  const { stacks } = projectTree(layout, ['results', 'description'], 1280, 900);
  const results = stacks.find((stack) => stack.panels.includes('results')).rect;
  const description = stacks.find((stack) =>
    stack.panels.includes('description')
  ).rect;
  assert(
    results[1] + results[3] <= description[1] + 0.001,
    'Description remains below Results even when another dock owns the right column'
  );
}
function resultsStack(layout) {
  return projectTree(layout, ['results', 'description'], 1280, 900).stacks.find(
    (stack) => stack.panels.includes('results')
  );
}

const base = process.argv[2],
  output = '../.screenshots/workspace-current';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 }
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
  const ready = () =>
    page.waitForFunction(
      () =>
        document.querySelector('.workspace') &&
        !document.querySelector('.workspace-results[aria-busy="true"]')
    );
  const tabs = page.locator('.workspace-tabs[data-kind="search"] [role="tab"]');
  const description = page.locator('[data-dock="description"]');
  const state = () =>
    page.evaluate(() =>
      JSON.parse(localStorage.getItem('tactic_stream.docks.admin'))
    );
  const root = page.locator('.dock-menu'),
    presets = page.locator('.dock-presets-menu');
  const titlebar = () => description.locator(':scope > header');
  async function position(action) {
    await titlebar()
      .getByLabel('Panel position: Description', { exact: true })
      .click();
    await description
      .getByRole('button', { name: action, exact: true })
      .click();
  }
  async function signIn(login = 'admin') {
    await page.getByLabel('Login', { exact: true }).fill(login);
    await page
      .getByLabel('Password', { exact: true })
      .fill('private-test-password');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await ready();
  }
  async function signOut() {
    await page.getByLabel('Account', { exact: true }).click();
    await page
      .locator('.account-menu')
      .getByRole('button', { name: 'Sign Out', exact: true })
      .click();
    await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor();
  }
  await page.goto(
    base + '/projects/one/?search_type=contract/quick_task&view=table'
  );
  await signIn();
  const firstId = await tabs.first().getAttribute('data-tab-id');
  await root.getByLabel('Workspace panels', { exact: true }).click();
  await root
    .locator('.dock-group-menu > summary[aria-label="Browsing"]')
    .click();
  await root
    .getByRole('menuitemradio', { name: 'Description', exact: true })
    .click();
  await description.waitFor({ state: 'visible' });
  const object = page
    .locator('.workspace-results .result-item:visible')
    .first();
  await object
    .getByRole('button', { name: 'Expand item', exact: true })
    .click();
  const process = page
    .locator(
      '.workspace-results .result-item-process[aria-label="Review"]:visible'
    )
    .first();
  assert.equal(
    await process
      .getByRole('button', { name: 'Expand item', exact: true })
      .count(),
    0,
    'Empty processes have no versions to expand'
  );
  await process.locator('.result-item-copy').click();
  const focusedTitle = await description
    .locator('.description-editor header strong')
    .innerText();
  assert.equal(focusedTitle, 'Review');
  await position('Dock right');
  const divider = page.getByRole('separator', {
    name: 'Resize workspace panels',
    exact: true
  });
  await divider.focus();
  await page.keyboard.press('ArrowRight');
  const ratio = (await state()).layout.ratio;
  assert(ratio > 0.5);
  const dividerBox = await divider.boundingBox();
  await page.mouse.move(dividerBox.x + 3, dividerBox.y + 30);
  await page.mouse.down();
  await page.mouse.move(dividerBox.x + 85, dividerBox.y + 30);
  await page.keyboard.press('Escape');
  await page.mouse.up();
  assert.equal(
    (await state()).layout.ratio,
    ratio,
    'Escape rolls back a splitter gesture'
  );
  await titlebar().screenshot({
    path: output + '/stream-dock-title.png',
    animations: 'disabled'
  });
  await position('Float panel');
  assert.equal(await description.locator('.dock-resize-edge').count(), 8);
  for (const [edge, cursor] of [
    ['left', 'ew-resize'],
    ['top', 'ns-resize'],
    ['top-left', 'nwse-resize'],
    ['top-right', 'nesw-resize']
  ]) {
    assert.equal(
      await description
        .locator('.dock-resize-edge.' + edge)
        .evaluate((node) => getComputedStyle(node).cursor),
      cursor
    );
  }
  const beforeResize = await description.boundingBox(),
    edge = await description.locator('.dock-resize-edge.left').boundingBox();
  await page.mouse.move(edge.x + 3, edge.y + 40);
  await page.mouse.down();
  await page.mouse.move(edge.x - 30, edge.y + 40, { steps: 5 });
  await page.mouse.up();
  assert(
    (await description.boundingBox()).width > beforeResize.width + 25,
    'Left edge resizes the floating panel'
  );
  const beforeDrag = await state(),
    grip = await description.locator('.dock-move-handle').boundingBox();
  assert.equal(
    await description.locator('button .dock-grip').count(),
    0,
    'The grip is a drag surface'
  );
  await page.mouse.move(grip.x + 10, grip.y + 12);
  await page.mouse.down();
  await page.mouse.move(grip.x + 75, grip.y + 60, { steps: 5 });
  await page.keyboard.press('Escape');
  await page.mouse.up();
  assert.deepEqual(
    await state(),
    beforeDrag,
    'Escape restores rectangle, tree and floating order'
  );
  await description.locator('.dock-move-handle').click({ button: 'right' });
  const context = page.locator('.dock-context-menu > .account-panel');
  await context.waitFor({ state: 'visible' });
  assert.equal(
    await context
      .getByRole('menuitem', { name: 'Dock to workspace', exact: true })
      .count(),
    1
  );
  await context.screenshot({
    path: output + '/stream-dock-context.png',
    animations: 'disabled'
  });
  await page.keyboard.press('End');
  await page.keyboard.press('Home');
  assert.equal(
    await context
      .getByRole('menuitem', { name: 'Help for this dock', exact: true })
      .evaluate((node) => node === document.activeElement),
    true
  );
  await page.keyboard.press('Escape');
  const floating = (await state()).panels.description.rect;
  await page
    .getByRole('button', { name: 'Add new search tab', exact: true })
    .click();
  await ready();
  const secondId = await tabs.last().getAttribute('data-tab-id'),
    secondTitle = await tabs.last().getAttribute('aria-label');
  await position('Dock panel');
  await position('Dock bottom');
  assertDescriptionBelowResults((await state()).layout);
  await page
    .getByLabel('Search objects', { exact: true })
    .fill('Second tab draft');
  await page.screenshot({
    path: output + '/stream-workspace-split.png',
    animations: 'disabled'
  });
  await page.locator('[role="tab"][data-tab-id="' + firstId + '"]').click();
  await ready();
  assert.equal((await state()).panels.description.floating, true);
  await page.waitForFunction(
    (title) =>
      document.querySelector('.description-editor header strong')
        ?.textContent === title,
    focusedTitle
  );
  assert.deepEqual((await state()).panels.description.rect, floating);
  await titlebar().getByLabel('Maximize panel', { exact: true }).click();
  await page.reload();
  await ready();
  await description.waitFor({ state: 'visible' });
  assert.equal(
    (await state()).maximized,
    'description',
    'Reload restores the expanded dock'
  );
  assertDescriptionBelowResults(
    await page.evaluate((secondId) => {
      const project = JSON.parse(
        localStorage.getItem('tactic_stream.workspace.admin')
      ).one;
      return project.sections
        .flatMap((section) => section.tabs)
        .find((tab) => tab.id === secondId).workspaceLayout.layout;
    }, secondId)
  );
  await page.waitForFunction(
    (title) =>
      document.querySelector('.description-editor header strong')
        ?.textContent === title,
    focusedTitle
  );
  assert.equal(
    await page
      .locator('[role="tab"][data-tab-id="' + firstId + '"]')
      .getAttribute('aria-selected'),
    'true'
  );
  assert(!new URL(page.url()).searchParams.has('tab'));
  await titlebar().getByLabel('Restore panel', { exact: true }).click();
  assert.deepEqual(
    (await state()).panels.description.rect,
    floating,
    'Restore keeps the original floating geometry'
  );
  await page.locator('[role="tab"][data-tab-id="' + secondId + '"]').click();
  await ready();
  assertDescriptionBelowResults((await state()).layout);
  assert.equal(
    await page.getByLabel('Search objects', { exact: true }).inputValue(),
    'Second tab draft'
  );
  await tabs
    .last()
    .locator('..')
    .getByLabel('Close search tab: ' + secondTitle, { exact: true })
    .click();
  await ready();
  await page.reload();
  await ready();
  assert.equal(await tabs.count(), 1);
  await page.locator('.workspace-tab-history > summary').click();
  await page
    .locator('.workspace-tab-history')
    .getByRole('menuitem', { name: secondTitle, exact: true })
    .click();
  await ready();
  assert.equal(
    await tabs.count(),
    2,
    'Recently closed tabs can be restored after reload'
  );
  assert.equal(
    await page.getByLabel('Search objects', { exact: true }).inputValue(),
    'Second tab draft'
  );
  assertDescriptionBelowResults((await state()).layout);
  await signOut();
  await signIn('workspace_user');
  assert.equal(
    await tabs.count(),
    0,
    'Another account has no inherited search tabs'
  );
  assert.equal(
    await description.isVisible(),
    false,
    'Another account has its own docks'
  );
  await signOut();
  await signIn();
  assert.equal(await tabs.count(), 2);
  assert.equal(
    await page.getByLabel('Search objects', { exact: true }).inputValue(),
    'Second tab draft'
  );
  assertDescriptionBelowResults((await state()).layout);
  await root.getByLabel('Workspace panels', { exact: true }).click();
  await root
    .locator(':scope > .account-panel')
    .screenshot({
      path: output + '/stream-dock-menu.png',
      animations: 'disabled'
    });
  await page.keyboard.press('Escape');
  await root.getByLabel('Workspace panels', { exact: true }).click();
  await presets.getByLabel('Layout presets', { exact: true }).click();
  await presets
    .locator(':scope > .account-panel')
    .screenshot({
      path: output + '/stream-presets.png',
      animations: 'disabled'
    });
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await selectProject(page, 'two');
  await ready();
  assert.equal(await tabs.count(), 0);
  await selectProject(page, 'one');
  await ready();
  assert.equal(await tabs.count(), 2);
  assertDescriptionBelowResults((await state()).layout);
  await position('Stack panels');
  const stackTabs = description.locator('[data-kind="dock"]');
  await stackTabs
    .getByRole('tab', { name: 'Description', exact: true })
    .focus();
  await page.keyboard.press('ArrowLeft');
  await page
    .locator('[data-dock="results"] [data-kind="dock"] [data-tab-id="results"]')
    .waitFor({ state: 'visible' });
  assert.equal(
    resultsStack((await state()).layout).active,
    'results',
    'Keyboard selects the other panel in a stack'
  );
  await page
    .locator('[data-dock="results"] [data-kind="dock"]')
    .getByRole('tab', { name: 'Description', exact: true })
    .click();
  const targetTab = stackTabs.getByRole('tab', {
    name: 'Description',
    exact: true
  });
  const targetBounds = await targetTab.boundingBox();
  await stackTabs
    .getByRole('tab', { name: 'Search', exact: true })
    .dragTo(targetTab, {
      targetPosition: {
        x: targetBounds.width * 0.75,
        y: targetBounds.height / 2
      }
    });
  assert.deepEqual(
    resultsStack((await state()).layout).panels,
    ['description', 'results'],
    'Dock stack reorders through the common tab control'
  );
  await page.mouse.move(600, 500);
  await titlebar().screenshot({
    path: output + '/stream-dock-stack-title.png',
    animations: 'disabled'
  });
  await page.reload();
  await ready();
  await description.waitFor({ state: 'visible' });
  assert.deepEqual(resultsStack((await state()).layout).panels, [
    'description',
    'results'
  ]);
  await titlebar().focus();
  await page.keyboard.press('Shift+F10');
  await context.waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
  assert.equal(
    await titlebar().evaluate((node) => node === document.activeElement),
    true,
    'Context Escape returns focus to its title bar'
  );
  assert.deepEqual(errors, []);
  console.log(
    'PASS: all-edge resize, grip context/keyboard, gesture rollback, tab layouts/maximize, reload/history, logout/account/project isolation and clean URLs'
  );
} finally {
  await browser.close();
}
