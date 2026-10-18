import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const base = process.argv[2],
  project = process.env.STREAM_CHECK_PROJECT;
async function request(path, values) {
  const response = await fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  const data = await response.json();
  assert(response.ok, data.error);
  return data.result;
}
const ticket = await request('/admin/rpc', {
  method: 'get_ticket',
  args: ['admin', process.env.STREAM_CHECK_PASSWORD]
});
const browser = await chromium.launch({ headless: true });
let page;
try {
  page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    colorScheme: 'dark',
    hasTouch: true
  });
  page.setDefaultTimeout(12000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() => {
    if (!localStorage.getItem('tactic_stream.appearance'))
      localStorage.setItem(
        'tactic_stream.appearance',
        JSON.stringify({ mode: 'dark', language: 'en' })
      );
  });
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
  await page.goto('http://tactic-stream.test/');
  await page
    .getByLabel('Login', { exact: true })
    .fill(process.env.STREAM_CHECK_LOGIN || 'admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.STREAM_CHECK_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const ready = () =>
    page.waitForFunction(
      () =>
        document.querySelector('.workspace-empty') ||
        document
          .querySelector('.workspace-results')
          ?.getAttribute('aria-busy') === 'false'
    );
  await ready();
  await selectProject(page, project);
  await page.goto(
    'http://tactic-stream.test/projects/' +
      encodeURIComponent(project) +
      '/?search_type=cg%2Fassets&view=table'
  );
  await ready();
  const open = async () => {
    await page.getByLabel('More options', { exact: true }).click();
    await page
      .locator('.settings-menu')
      .getByRole('button', { name: 'Script Editor', exact: true })
      .click();
    await page.waitForFunction(
      () =>
        document
          .querySelector('.script-editor-dialog')
          ?.getAttribute('aria-busy') === 'false'
    );
  };
  const dialog = page.locator('.script-editor-dialog');
  const source = dialog.getByLabel('Script source', { exact: true });
  const idle = () =>
    page.waitForFunction(
      () =>
        document
          .querySelector('.script-editor-dialog')
          ?.getAttribute('aria-busy') === 'false'
    );
  await open();
  await source.waitFor();
  const original =
    'def hello(name):\n    # Demo server script\n    return {"greeting": name}\n\nreturn hello("World")\n';
  await dialog.getByLabel('Script folder', { exact: true }).fill('editor_demo');
  await dialog.getByLabel('Script title', { exact: true }).fill('hello');
  await source.fill(original);
  await source.press('Control+s');
  await idle();
  await dialog.getByRole('button', { name: 'Run Script', exact: true }).click();
  await idle();
  assert(
    (await dialog.locator('.script-editor-output pre').innerText()).includes(
      'World'
    )
  );
  assert.equal(
    await dialog.locator('.code-highlight .syntax-keyword').first().innerText(),
    'def'
  );
  assert.equal(
    (await dialog.locator('.script-editor-toolbar').boundingBox()).height,
    32
  );
  assert.equal(
    (await dialog.locator('.script-editor-output').boundingBox()).height,
    120
  );
  assert.equal(
    (
      await dialog
        .locator('.script-editor-tree .workspace-search')
        .boundingBox()
    ).height,
    36
  );
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-script-editor.png',
    animations: 'disabled'
  });
  // Search/replace, occurrences, comments, per-buffer undo, outline and selection execution.
  await source.press('Control+h');
  await dialog.getByLabel('Find in source', { exact: true }).fill('World');
  assert.equal(await dialog.locator('.syntax-search').count(), 1);
  await dialog.getByLabel('Find in source', { exact: true }).press('Tab');
  assert.equal(
    await source.inputValue(),
    original,
    'Tab in search traverses controls without indenting source'
  );
  await dialog.getByLabel('Replacement', { exact: true }).fill('Earth');
  await dialog
    .getByRole('button', { name: 'Replace all', exact: true })
    .click();
  assert((await source.inputValue()).includes('Earth'));
  await source.press('Control+z');
  assert.equal(await source.inputValue(), original);
  await dialog.getByLabel('Close search', { exact: true }).click();
  await source.fill('server.que');
  await source.press('Control+End');
  await source.press('Control+Space');
  await dialog.getByRole('option', { name: 'query', exact: true }).click();
  assert.equal(await source.inputValue(), 'server.query()');
  assert.equal(
    await source.evaluate((node) => node.selectionStart),
    'server.query('.length
  );
  await dialog
    .getByLabel('Script language', { exact: true })
    .selectOption('server_js');
  await source.fill(
    'return {ping: server.ping(), project: server.get_project()};'
  );
  await source.press('Control+s');
  await idle();
  await dialog.getByRole('button', { name: 'Run Script', exact: true }).click();
  await idle();
  assert(
    (await dialog.locator('.script-editor-output pre').innerText()).includes(
      'OK'
    )
  );
  assert.equal(
    await dialog.locator('.code-highlight .syntax-keyword').first().innerText(),
    'return'
  );
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-script-editor-server-js.png',
    animations: 'disabled'
  });
  await source.fill('const custom = 1;\ncus');
  await dialog
    .getByLabel('Script language', { exact: true })
    .selectOption('javascript');
  await source.press('Control+End');
  await source.press('Control+Space');
  await dialog.getByRole('option', { name: 'custom', exact: true }).click();
  assert((await source.inputValue()).endsWith('custom'));
  const control = page.locator('.system-activity-control');
  for (const fails of [false, true]) {
    await source.fill(
      'await new Promise(resolve => { window.addEventListener("stream-script-release", resolve, {once: true}); document.body.dataset.editorWaiting = "true"; }); document.body.dataset.editorWaiting = "";\n' +
        (fails
          ? 'throw new Error("Browser execution failed");'
          : 'return "Async browser result";')
    );
    await dialog
      .getByRole('button', { name: 'Run Script', exact: true })
      .click();
    await page.waitForFunction(
      () => document.body.dataset.editorWaiting === 'true'
    );
    await dialog.locator('.notification-card[data-kind="progress"]').waitFor();
    assert.equal(
      await control
        .getByLabel('System activity', { exact: true })
        .getAttribute('title'),
      'Running…'
    );
    assert.equal(await control.locator('.busy-indicator.running').count(), 1);
    assert(
      await dialog
        .getByLabel('Close script editor', { exact: true })
        .isDisabled()
    );
    if (!fails) {
      for (const width of [1440, 360, 320]) {
        await page.setViewportSize({
          width,
          height: width === 1440 ? 1000 : 740
        });
        assert(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth
          )
        );
        await page.screenshot({
          path: `../.screenshots/handler-current/stream-script-running-${width}.png`,
          animations: 'disabled'
        });
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
    }
    await page.evaluate(() =>
      window.dispatchEvent(new Event('stream-script-release'))
    );
    await idle();
    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.system-activity-control .busy-indicator.running'
        )
    );
    assert.equal(
      await dialog.locator('.notification-card[data-kind="progress"]').count(),
      0
    );
    assert(
      (await dialog.locator('.script-editor-output pre').innerText()).includes(
        fails ? 'Browser execution failed' : 'Async browser result'
      )
    );
    if (fails)
      assert(
        (await dialog.locator('p[role="alert"]').innerText()).includes(
          'Browser execution failed'
        )
      );
  }
  await source.fill(
    'const marker = "<img src=x onerror=alert(1)>";\nconsole.log("Browser stdout");\nconst cyclic = {}; cyclic.self = cyclic; console.log(cyclic);\nreturn {project, runtime: "browser"};'
  );
  await dialog.getByRole('button', { name: 'Run Script', exact: true }).click();
  await idle();
  assert(
    (await dialog.locator('.script-editor-output pre').innerText()).includes(
      'browser'
    )
  );
  assert(
    (await dialog.locator('.script-editor-output pre').innerText()).includes(
      'Browser stdout'
    )
  );
  assert.equal(
    await dialog.getByRole('alert').count(),
    0,
    (await dialog.getByRole('alert').allTextContents()).join('\n')
  );
  assert.equal(await dialog.locator('.code-highlight img').count(), 0);
  await source.press('Control+s');
  await idle();
  // A clean restored tab follows external edits; dirty tabs below retain their own source.
  await dialog.getByLabel('Close script editor', { exact: true }).click();
  const catalog = await request('/admin/script-editor/read', {
    ticket,
    project
  });
  const saved = catalog.scripts.find(
    (row) => row.folder === 'editor_demo' && row.title === 'hello'
  );
  await request('/admin/script-editor/save', {
    ticket,
    project,
    code: saved.code,
    revision: saved.revision,
    folder: saved.folder,
    title: saved.title,
    language: saved.language,
    source: saved.source + '\n// remote change'
  });
  await page.reload();
  await ready();
  await open();
  assert((await source.inputValue()).endsWith('// remote change'));
  assert.equal(await dialog.locator('.workspace-tab.dirty').count(), 0);
  await page.evaluate(() => {
    document.execCommand = (command) => {
      if (command === 'copy')
        window.copiedRunner = document.activeElement.value;
      return command === 'copy';
    };
  });
  await dialog.getByLabel('Saved script actions', { exact: true }).click();
  await dialog
    .getByRole('button', { name: 'Copy Script Runner', exact: true })
    .click();
  const runner = await page.evaluate(() => window.copiedRunner);
  assert(runner.includes("rpc('query'"));
  assert(!runner.includes('ticket'));
  await source.fill(runner);
  await dialog.getByRole('button', { name: 'Run Script', exact: true }).click();
  await idle();
  assert.equal(await dialog.getByRole('alert').count(), 0);
  await source.fill('return {selection: true};\nreturn {whole: true};');
  await source.evaluate((node) => {
    node.focus();
    node.setSelectionRange(0, 25);
    node.dispatchEvent(new Event('select'));
  });
  await source.press('Control+Space');
  await dialog
    .getByRole('listbox', { name: 'Code completions', exact: true })
    .waitFor();
  await source.press('Control+Enter');
  await idle();
  assert(
    (await dialog.locator('.script-editor-output pre').innerText()).includes(
      '"selection": true'
    )
  );
  await dialog
    .getByLabel('Script language', { exact: true })
    .selectOption('python');
  await source.fill(original.replace('World', 'Second'));
  await source.press('Control+s');
  await idle();
  await dialog.getByLabel('Saved revisions', { exact: true }).click();
  await idle();
  const history = page.getByRole('dialog', {
    name: 'Saved revisions',
    exact: true
  });
  assert((await history.locator(':scope > .app-button').count()) >= 2);
  await history.locator(':scope > .app-button').last().click();
  await idle();
  assert.equal(await source.inputValue(), original);
  assert.equal(await dialog.locator('.workspace-tab.dirty').count(), 1);
  await dialog.getByRole('radio', { name: 'Outline', exact: true }).click();
  await dialog.getByRole('button', { name: 'hello · 1', exact: true }).click();
  assert.equal(await source.evaluate((node) => node.selectionStart), 0);
  // Native AST excludes strings, retains nested method names and fills callable parentheses.
  const structure =
    '"""def fake(): ignored"""\nclass Worker:\n    def work(self, name="demo"):\n        """Run a job."""\n        return name\n    def next(self):\n        return self.wo';
  await source.fill(structure);
  await source.press('Control+End');
  await source.press('Control+Space');
  const work = dialog.getByRole('option', { name: 'work', exact: true });
  assert((await work.innerText()).includes('Run a job.'));
  assert((await work.innerText()).includes('(self, name='));
  assert.equal(
    await work.evaluate((node) => getComputedStyle(node).borderRadius),
    '9px'
  );
  assert.notEqual(
    await work.evaluate((node) => getComputedStyle(node).backgroundColor),
    await dialog
      .getByRole('button', { name: 'Run Script', exact: true })
      .evaluate((node) => getComputedStyle(node).backgroundColor)
  );
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-script-completion.png',
    animations: 'disabled'
  });
  await source.press('Tab');
  assert((await source.inputValue()).endsWith('self.work()'));
  assert.equal(
    await source.evaluate((node) => node.value.slice(node.selectionStart)),
    ')'
  );
  await source.press('Control+Shift+o');
  await dialog
    .getByRole('button', { name: 'Worker.work · 3', exact: true })
    .waitFor();
  assert.equal(
    await dialog.getByRole('button', { name: 'fake · 1', exact: true }).count(),
    0
  );
  await dialog
    .getByLabel('Search scripts and symbols', { exact: true })
    .fill('Worker.work');
  assert.equal(
    await dialog.locator('.script-editor-outline .app-button').count(),
    1
  );
  await dialog
    .getByRole('button', { name: 'Worker.work · 3', exact: true })
    .click();
  assert.equal(
    await source.evaluate(
      (node) => node.value.slice(0, node.selectionStart).split('\n').length
    ),
    3
  );
  await source.press('Alt+ArrowDown');
  assert.equal(
    await source.evaluate(
      (node) => node.value.slice(0, node.selectionStart).split('\n').length
    ),
    6
  );
  await source.evaluate((node) => {
    node.focus();
    const position = node.value.indexOf('work()') + 2;
    node.setSelectionRange(position, position);
    node.dispatchEvent(new Event('select'));
  });
  await source.press('F12');
  assert.equal(
    await source.evaluate(
      (node) => node.value.slice(0, node.selectionStart).split('\n').length
    ),
    3
  );
  await dialog
    .getByLabel('Search scripts and symbols', { exact: true })
    .fill('');
  await page.screenshot({
    path: '../.screenshots/handler-current/stream-script-outline.png',
    animations: 'disabled'
  });
  await source.fill('print');
  await source.press('Control+End');
  await source.press('Tab');
  assert.equal(
    await source.inputValue(),
    'print   ',
    'Native Tab inserts to the next stop at the caret'
  );
  await source.fill('import json as data\ndata.du');
  await source.press('Control+End');
  await source.press('Control+Space');
  await dialog.getByRole('option', { name: 'dumps', exact: true }).click();
  assert((await source.inputValue()).endsWith('data.dumps()'));
  assert.equal(
    await dialog.locator('.syntax-module').first().innerText(),
    'data'
  );
  // A response for an old source must not replace the new source's suggestions.
  let release, reached;
  const held = new Promise((resolve) => {
      release = resolve;
    }),
    received = new Promise((resolve) => {
      reached = resolve;
    });
  const holdOldAnalysis = async (route) => {
    if (route.request().postDataJSON().source === 'server.que') {
      reached();
      await held;
    }
    await route.fallback();
  };
  await page.route('**/admin/script-editor/analyse', holdOldAnalysis);
  try {
    const oldReply = page.waitForResponse(
      (response) =>
        response.url().endsWith('/admin/script-editor/analyse') &&
        response.request().postDataJSON().source === 'server.que'
    );
    await source.fill('server.que');
    await source.press('Control+End');
    await source.press('Control+Space');
    await received;
    await source.fill('import json as data\ndata.du');
    await source.press('Control+End');
    await source.press('Control+Space');
    await dialog.getByRole('option', { name: 'dumps', exact: true }).waitFor();
    release();
    await (await oldReply).finished();
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    assert.equal(
      await dialog.getByRole('option', { name: 'query', exact: true }).count(),
      0
    );
  } finally {
    release();
    await page.unroute('**/admin/script-editor/analyse', holdOldAnalysis);
  }
  await source.press('Escape');
  await source.fill(original);
  // Preserve a dirty saved tab and a new tab across an HTTP browser reload.
  await dialog.getByRole('button', { name: 'New script', exact: true }).click();
  await dialog.getByLabel('Text size', { exact: true }).selectOption('11');
  await dialog.getByLabel('Script title', { exact: true }).fill('draft');
  await source.fill('return {draft: true};');
  await dialog
    .getByLabel('Script language', { exact: true })
    .selectOption('javascript');
  await dialog.getByLabel('Close script editor', { exact: true }).click();
  await page.reload();
  await ready();
  await open();
  assert.equal(await source.inputValue(), 'return {draft: true};');
  assert.equal(await dialog.getByRole('tab').count(), 2);
  assert.equal(
    await dialog
      .locator('.code-editor')
      .evaluate((node) => node.style.getPropertyValue('--code-size')),
    '11pt'
  );
  const scriptTabs = dialog.getByRole('tab');
  const scriptOrder = await scriptTabs.evaluateAll((nodes) =>
    nodes.map((node) => node.dataset.tabId)
  );
  const start = await scriptTabs.nth(0).boundingBox(),
    finish = await scriptTabs.nth(1).boundingBox();
  await page.mouse.move(start.x + start.width / 2, start.y + start.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    finish.x + finish.width / 2,
    finish.y + finish.height / 2,
    { steps: 5 }
  );
  await dialog.locator('.workspace-tab.dragging').waitFor();
  assert.equal(
    await source.inputValue(),
    'return {draft: true};',
    'Dragging an inactive script keeps the active draft'
  );
  await page.mouse.up();
  assert.deepEqual(
    await scriptTabs.evaluateAll((nodes) =>
      nodes.map((node) => node.dataset.tabId)
    ),
    [...scriptOrder].reverse()
  );
  await dialog.getByLabel('Close script editor', { exact: true }).click();
  await page.reload();
  await ready();
  await open();
  assert.deepEqual(
    await scriptTabs.evaluateAll((nodes) =>
      nodes.map((node) => node.dataset.tabId)
    ),
    [...scriptOrder].reverse(),
    'Script drag order survives reload'
  );
  assert.equal(await source.inputValue(), 'return {draft: true};');
  await dialog.getByRole('tab', { name: 'hello', exact: true }).click();
  assert.equal(await source.inputValue(), original);
  for (const width of [360, 320]) {
    await page.setViewportSize({ width, height: 740 });
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    const overflow = await dialog.evaluate((node) =>
      [...node.querySelectorAll('*')]
        .filter(
          (child) =>
            child.getBoundingClientRect().right >
            node.getBoundingClientRect().right + 1
        )
        .slice(0, 15)
        .map((child) => [
          child.className,
          child.getBoundingClientRect().x,
          child.getBoundingClientRect().width
        ])
    );
    assert(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
      JSON.stringify(overflow)
    );
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      )
    );
    assert((await dialog.locator('.code-buffer').boundingBox()).height > 100);
    await page.screenshot({
      path: `../.screenshots/handler-current/stream-script-editor-${width}.png`,
      animations: 'disabled'
    });
  }
  await source.fill('import json as data\ndata.du');
  await source.press('Control+End');
  await source.press('Control+Space');
  await dialog.getByRole('option', { name: 'dumps', exact: true }).tap();
  assert((await source.inputValue()).endsWith('data.dumps()'));
  await dialog.getByLabel('Close all script tabs', { exact: true }).tap();
  const confirm = page.getByRole('dialog', {
    name: 'Save changes before closing?',
    exact: true
  });
  await confirm.waitFor();
  await confirm.getByRole('button', { name: 'Cancel', exact: true }).tap();
  assert.equal(await dialog.getByRole('tab').count(), 2);
  await dialog.getByLabel('Close all script tabs', { exact: true }).tap();
  await confirm.getByRole('button', { name: 'Discard', exact: true }).tap();
  assert.equal(await dialog.getByRole('tab').count(), 0);
  await dialog.getByLabel('Close script editor', { exact: true }).tap();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => {
    const settings = JSON.parse(
      localStorage.getItem('tactic_stream.appearance')
    );
    settings.language = 'ru';
    localStorage.setItem('tactic_stream.appearance', JSON.stringify(settings));
  });
  await page.reload();
  await ready();
  const ru = JSON.parse(
    readFileSync(new URL('../src/locales/ru.json', import.meta.url), 'utf8')
  );
  await page.getByLabel(ru['More options'], { exact: true }).click();
  await page
    .locator('.settings-menu')
    .getByRole('button', { name: ru['Script Editor'], exact: true })
    .click();
  await idle();
  await dialog.getByLabel(ru['Script source'], { exact: true }).waitFor();
  await dialog
    .getByLabel(ru['Save current script to server'], { exact: true })
    .click();
  await idle();
  assert(
    (await dialog.locator('p[role="alert"]').innerText()).includes(
      ru['Folder and title must form a valid script path']
    )
  );
  await dialog.getByLabel(ru['Close script editor'], { exact: true }).click();
  assert.deepEqual(errors, []);
  console.log(
    'PASS Script Editor: native toolbar/output, Python and browser JS under HTTP/CSP, editing/search/undo/completion/outline, audit revisions, per-tab drafts/reload, touch320/360'
  );
} finally {
  try {
    await page?.unrouteAll({ behavior: 'wait' });
  } finally {
    await browser.close();
  }
}
