import assert from 'node:assert/strict';
import { chromium } from 'playwright';

// Read-only journey against a project with an assigned sidebar Saved Search.
const base = process.argv[2],
  project = process.env.STREAM_CHECK_PROJECT;
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1380, height: 820 } });
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const read = () =>
  page.evaluate(() => {
    const app =
      document.querySelector('#app').__vue_app__._container._vnode.component
        .subTree.component.subTree.component.proxy;
    return { links: app.flatViewLinks, sections: app.activeWorkspace.sections };
  });
const ready = () =>
  page.locator('.workspace-results[aria-busy="false"]').waitFor();
async function open(entry) {
  await page
    .getByRole('button', { name: 'Open navigation', exact: true })
    .first()
    .click();
  await page
    .locator('#workspace-sidebar [data-entry-key="' + entry.key + '"]')
    .click();
}
try {
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.goto(base + '/projects/' + project + '/');
  await page
    .getByLabel('Login', { exact: true })
    .fill(process.env.STREAM_CHECK_LOGIN || 'admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('.workspace-empty').waitFor();
  const entry = (await read()).links.find(
    (link) =>
      link.supported &&
      link.display.options.search_view &&
      !link.layoutView &&
      (!process.env.STREAM_CHECK_SEARCH_TYPE ||
        link.search_type === process.env.STREAM_CHECK_SEARCH_TYPE)
  );
  assert.ok(
    entry,
    'Fixture needs a sidebar item with an assigned Saved Search'
  );
  let release, arrived;
  const received = new Promise((resolve) => (arrived = resolve));
  const held = new Promise((resolve) => (release = resolve));
  let count = 0,
    assigned,
    withSibling = false;
  await page.route('**/admin/search-configuration/settings', async (route) => {
    const response = await route.fetch(),
      body = await response.json();
    assigned = body.result.presets.find(
      (p) => p.view === entry.display.options.search_view
    );
    if (withSibling) {
      assigned = {
        ...assigned,
        records: [
          {
            column: 'code',
            relation: '=',
            value: '__READ_ONLY_TEST__',
            rowEnabled: true,
            operator: 'begin'
          }
        ],
        keyword: 'Read-only fixture',
        order_bys: ['code desc']
      };
      body.result.presets = [
        assigned,
        {
          ...assigned,
          code: 'OTHER',
          view: 'link_search:other:' + entry.search_type + '@' + entry.name,
          records: [],
          keyword: ''
        }
      ];
    }
    if (++count === 1) {
      arrived();
      await held;
    }
    await route.fulfill({ response, json: body });
  });
  await open(entry);
  await received;
  await open(entry);
  await ready();
  release();
  await page.waitForTimeout(150);
  let state = await read();
  assert.equal(
    state.sections.length,
    1,
    'Concurrent openings create one section'
  );
  assert.equal(
    state.sections[0].tabs.filter((t) => t.state.savedSearch === assigned.view)
      .length,
    1
  );
  assert.equal(
    state.sections[0].tabs.length,
    1,
    'Assigned search replaces the empty base search'
  );
  assert.deepEqual(
    state.sections[0].tabs[0].state.filterRecords,
    assigned.records
  );
  assert.deepEqual(
    state.sections[0].tabs[0].state.presetOrderBys,
    assigned.order_bys
  );
  const baseId = state.sections[0].tabs[0].id;
  for (let index = 0; index < 3; index++) {
    await open(entry);
    await ready();
  }
  assert.equal((await read()).sections[0].tabs[0].id, baseId);
  await page
    .getByRole('button', { name: 'Add new search tab', exact: true })
    .click();
  await ready();
  await page
    .getByLabel('Search objects', { exact: true })
    .fill('Unsubmitted personal search');
  state = await read();
  const personalId = state.sections[0].current;
  await open(entry);
  await ready();
  assert.equal(
    (await read()).sections[0].current,
    personalId,
    'Sidebar retains the selected personal tab'
  );
  await page.reload();
  await ready();
  state = await read();
  assert.equal(state.sections.length, 1);
  assert.equal(
    state.sections[0].tabs.length,
    2,
    'Explicit + tab survives reload'
  );
  assert.equal(state.sections[0].current, personalId);
  assert.equal(
    await page.getByLabel('Search objects', { exact: true }).inputValue(),
    'Unsubmitted personal search'
  );
  assert.deepEqual(errors, []);
  if (process.argv[3]) await page.screenshot({ path: process.argv[3] });
  withSibling = true;
  await page.evaluate(() => {
    const app =
      document.querySelector('#app').__vue_app__._container._vnode.component
        .subTree.component.subTree.component.proxy;
    app.workspaceProjects = {};
    localStorage.removeItem('tactic_stream.workspace.' + app.session.login);
  });
  await page.goto(base + '/projects/' + project + '/');
  await page.locator('.workspace-empty').waitFor();
  await open(entry);
  await ready();
  state = await read();
  assert.equal(
    state.sections[0].tabs.length,
    2,
    'Another preset with the same title remains a distinct search'
  );
  const initial = state.sections[0].tabs[0];
  assert.equal(initial.state.savedSearch, assigned.view);
  assert.deepEqual(initial.state.filterRecords, assigned.records);
  assert.equal(initial.state.searchText, assigned.keyword);
  assert.deepEqual(initial.state.presetOrderBys, assigned.order_bys);
  assert.deepEqual(errors, []);
  console.log(
    'PASS: assigned search filters/order, delayed repeated clicks, personal tabs/reload and distinct same-title presets'
  );
} finally {
  await browser.close();
}
