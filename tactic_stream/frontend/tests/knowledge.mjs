import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { build } from 'vite';
const [base, output, articleId, sectionId] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true }),
  page = await browser.newPage({ viewport: { width: 1440, height: 940 } });
page.setDefaultTimeout(12000);
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const panel = page.locator('[data-dock="knowledge"]'),
  content = page.locator('.knowledge-base');
async function capture(name) {
  const saved = await content.getAttribute('style');
  await content.evaluate((element) => {
    element._parent = element.parentNode;
    element._next = element.nextSibling;
    document.body.append(element);
  });
  try {
    for (const [width, height] of [
      [440, 650],
      [1200, 760]
    ]) {
      await content.evaluate(
        (element, { width, height }) =>
          Object.assign(element.style, {
            position: 'fixed',
            left: '0',
            top: '0',
            width: width + 'px',
            height: height + 'px',
            zIndex: '10000'
          }),
        { width, height }
      );
      await page.waitForTimeout(160);
      await page.evaluate(() => document.fonts.ready);
      await content.screenshot({
        path: `${output}/stream-${name}-${width}.png`,
        animations: 'disabled'
      });
      assert.ok(
        await content.evaluate(
          (element) => element.scrollWidth <= element.clientWidth + 1
        ),
        `${name} ${width} overflow`
      );
    }
  } finally {
    await content.evaluate((element, saved) => {
      element._parent.insertBefore(element, element._next);
      delete element._parent;
      delete element._next;
      if (saved === null) element.removeAttribute('style');
      else element.setAttribute('style', saved);
    }, saved);
    await page.waitForTimeout(160);
  }
}
async function choose(id, name) {
  const entry = panel
    .locator(`[data-knowledge-entry="${id}"]`)
    .getByRole('button', { name, exact: true });
  if (!(await entry.isVisible()))
    await panel
      .getByRole('button', { name: 'Back to articles', exact: true })
      .click();
  await entry.click();
  await panel.getByRole('heading', { level: 3 }).waitFor();
}
try {
  const unit = await build({
    configFile: false,
    logLevel: 'silent',
    build: {
      write: false,
      minify: false,
      lib: { entry: 'src/features/knowledge/markdown.js', formats: ['es'] }
    }
  });
  const moduleUrl =
    'data:text/javascript;base64,' +
    Buffer.from(
      unit[0].output.find((item) => item.type === 'chunk').code
    ).toString('base64');
  await page.evaluate(async (url) => {
    const { articleHtml, htmlMarkdown, plainText } = await import(url);
    const roundTrip = (markdown) => {
      const root = document.createElement('div');
      root.innerHTML = articleHtml(markdown, 'one');
      return htmlMarkdown(root);
    };
    const check = (condition, message) => {
      if (!condition) throw Error(message);
    };
    const source =
      '# Heading {align=center}\n\n- [x] Done\n  - Nested\n\n![Image](https://example.com/pic.png){width=320 height=180 fit=content}\n\n```python\nprint("ready")\n\n```';
    const result = roundTrip(source);
    check(
      result.includes('# Heading {align=center}'),
      'Heading alignment lost'
    );
    check(
      result.includes('- [x] Done') && result.includes('  - Nested'),
      'Checklist or nesting lost: ' + JSON.stringify(result)
    );
    check(
      result.includes('{width=320 height=180 fit=content}'),
      'Image dimensions lost'
    );
    check(result.includes('```python'), 'Code language lost');
    check(
      plainText('# Title\n\nBody').includes('Title\n'),
      'Full-text block boundaries lost'
    );
    const unsafe = articleHtml(
      '<img src="javascript:alert(1)" onerror="alert(1)"><script>alert(1)</script><a href="javascript:alert(1)">bad</a>'
    );
    check(
      !unsafe.includes('javascript:') &&
        !unsafe.includes('onerror') &&
        !unsafe.includes('<script'),
      'Unsafe article HTML'
    );
    check(
      articleHtml('skey://contract/entity?project=one&code=A').includes(
        'data-link="skey://'
      ),
      'Plain skey not linked'
    );
    check(roundTrip('A\n\n\n\nB').includes('<br />'), 'Blank author rows lost');
    check(
      roundTrip('`` code ` value ``').includes('code ` value'),
      'Inline backtick lost'
    );
    check(
      articleHtml('````python\n```\n\n\nend\n````').includes('\n\n\nend'),
      'Long fenced code changed'
    );
    check(
      roundTrip('| **Title** |\n| --- |\n| Value |').includes('**Title**'),
      'Table formatting lost'
    );
  }, moduleUrl);
  await page.addInitScript(() =>
    localStorage.setItem(
      'tactic_stream.appearance',
      JSON.stringify({ mode: 'dark', language: 'en' })
    )
  );
  await page.goto(base + '/projects/one/');
  await page.getByLabel('Login', { exact: true }).fill('admin');
  await page
    .getByLabel('Password', { exact: true })
    .fill('private-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByLabel('Workspace panels', { exact: true }).click();
  await page.getByLabel('Browsing', { exact: true }).click();
  await page
    .getByRole('menuitemradio', { name: 'Knowledge Base', exact: true })
    .click();
  await panel.waitFor();
  await panel
    .getByRole('button', { name: 'Create article', exact: true })
    .waitFor();
  await capture('catalog');
  const section = panel.locator(`[data-knowledge-entry="${sectionId}"]`);
  await choose(sectionId, 'Pipeline guide');
  await panel
    .getByRole('heading', { name: 'Pipeline guide', exact: true })
    .waitFor();
  await capture('section');
  await choose(articleId, 'Publishing guide');
  await panel
    .locator('.knowledge-document')
    .getByRole('heading', { name: 'Publish', exact: true })
    .waitFor();
  await capture('reader');
  assert.equal(
    (await panel.locator('.knowledge-document .syntax-string').count()) > 0,
    true
  );
  await panel.getByRole('button', { name: 'Edit', exact: true }).click();
  await panel
    .getByRole('textbox', { name: 'Article content', exact: true })
    .waitFor();
  await capture('editor');
  await panel
    .getByRole('button', { name: 'Show title and summary', exact: true })
    .click();
  await panel
    .getByLabel('Title', { exact: true })
    .fill('Publishing guide revised');
  await capture('metadata');
  await panel.getByRole('radio', { name: 'Markdown', exact: true }).click();
  const source = panel.getByRole('textbox', {
    name: 'Markdown source',
    exact: true
  });
  const original = await source.inputValue();
  await source.fill(original + '\n\nDraft survives navigation.');
  await capture('markdown');
  await page.reload();
  await panel
    .getByRole('heading', { name: 'Edit article', exact: true })
    .waitFor();
  await panel.getByRole('radio', { name: 'Markdown', exact: true }).click();
  assert.ok(
    (
      await panel.getByLabel('Markdown source', { exact: true }).inputValue()
    ).includes('Draft survives navigation.')
  );
  assert.ok(
    new URL(page.url()).searchParams
      .get('link')
      ?.startsWith('skey://one/th_knowledge_article?project=one&code=')
  );
  await choose(sectionId, 'Pipeline guide');
  await panel
    .getByRole('heading', { name: 'Pipeline guide', exact: true })
    .waitFor();
  await choose(articleId, 'Publishing guide revised');
  await panel
    .getByRole('heading', { name: 'Edit article', exact: true })
    .waitFor();
  await panel.getByRole('radio', { name: 'Markdown', exact: true }).click();
  assert.ok(
    (
      await panel.getByLabel('Markdown source', { exact: true }).inputValue()
    ).includes('Draft survives navigation.')
  );
  await panel.getByRole('button', { name: 'Save', exact: true }).click();
  await panel
    .getByRole('heading', { name: 'Publishing guide revised', exact: true })
    .waitFor();
  await panel.getByLabel('Change history', { exact: true }).click();
  const history = panel.locator('.knowledge-history-menu .account-panel');
  await history
    .getByRole('button', { name: 'Publishing guide', exact: true })
    .first()
    .waitFor();
  await history.screenshot({
    path: output + '/stream-history.png',
    animations: 'disabled'
  });
  await history
    .getByRole('button', { name: 'Publishing guide', exact: true })
    .last()
    .click();
  await panel
    .getByText('Previewing an earlier revision', { exact: false })
    .waitFor();
  assert.equal(
    (await panel.locator('.knowledge-document').innerText()).includes(
      'Draft survives navigation.'
    ),
    false
  );
  await panel
    .getByRole('button', { name: 'Return to current article', exact: true })
    .click();
  await panel
    .getByRole('button', { name: 'Create article', exact: true })
    .click();
  await panel.getByLabel('Title', { exact: true }).fill('Local new article');
  await panel.getByLabel('Summary', { exact: true }).fill('New local document');
  await capture('create');
  assert.equal(new URL(page.url()).searchParams.get('link'), null);
  await page.reload();
  await panel.getByLabel('Title', { exact: true }).waitFor();
  assert.equal(
    await panel.getByLabel('Title', { exact: true }).inputValue(),
    'Local new article'
  );
  await panel
    .getByRole('button', { name: 'Continue to content', exact: true })
    .click();
  await panel.getByRole('radio', { name: 'Markdown', exact: true }).click();
  await panel
    .getByLabel('Markdown source', { exact: true })
    .fill('# Test\n\nNew article body.');
  const draftReply = page.waitForResponse((response) =>
    response.url().endsWith('/knowledge/save_draft')
  );
  await panel
    .getByRole('button', { name: 'Save as draft', exact: true })
    .click();
  assert.equal((await (await draftReply).json()).result.document.draft, true);
  await panel.getByRole('button', { name: 'Publish', exact: true }).waitFor();
  await panel.getByRole('button', { name: 'Publish', exact: true }).click();
  await panel
    .getByRole('heading', { name: 'Local new article', exact: true })
    .waitFor();
  await panel.getByRole('button', { name: 'Edit', exact: true }).click();
  await panel
    .getByRole('button', { name: 'More formatting actions', exact: true })
    .click();
  await panel
    .getByRole('menuitem', { name: 'Show attached files', exact: true })
    .click();
  await panel.locator('input[type="file"]').setInputFiles({
    name: 'тест.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Knowledge attachment')
  });
  await panel
    .locator('.knowledge-library-file')
    .getByText('тест.txt', { exact: true })
    .waitFor();
  await capture('attachments');
  await panel.locator('.knowledge-library-file .attachment-card').click();
  await panel.getByRole('radio', { name: 'Markdown', exact: true }).click();
  assert.ok(
    (
      await panel.getByLabel('Markdown source', { exact: true }).inputValue()
    ).includes('[тест.txt](')
  );
  await panel.locator('input[type="file"]').setInputFiles({
    name: 'preview.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==',
      'base64'
    )
  });
  const picture = panel
    .locator('.knowledge-library-file')
    .filter({ hasText: 'preview.png' });
  await panel.getByRole('radio', { name: 'Visual', exact: true }).click();
  await picture.waitFor();
  await picture.locator('.attachment-card').click();
  const image = panel.locator('.knowledge-visual img');
  await image.waitFor();
  await image.click();
  await panel
    .getByLabel('Fixed image width', { exact: true })
    .evaluate((element) => {
      element.value = '320';
      element.dispatchEvent(new Event('input', { bubbles: true }));
    });
  assert.equal(await image.getAttribute('width'), '320');
  await panel.getByRole('radio', { name: 'Markdown', exact: true }).click();
  assert.ok(
    (
      await panel.getByLabel('Markdown source', { exact: true }).inputValue()
    ).includes('{width=320')
  );
  await panel.getByRole('button', { name: 'Save', exact: true }).click();
  await panel
    .getByRole('heading', { name: 'Local new article', exact: true })
    .waitFor();
  await panel
    .getByRole('button', { name: 'Delete article', exact: true })
    .click();
  const deletion = page.getByRole('dialog', {
    name: 'Delete record',
    exact: true
  });
  await deletion.waitFor();
  await deletion.getByRole('button', { name: 'Delete', exact: true }).click();
  await deletion.waitFor({ state: 'hidden' });
  assert.equal(
    await panel
      .getByRole('button', { name: 'Local new article', exact: true })
      .count(),
    0
  );
  await page.reload();
  await panel.waitFor();
  await panel.locator('.knowledge-tree').waitFor({ state: 'attached' });
  await panel.locator('.knowledge-loading').waitFor({ state: 'hidden' });
  if (
    !(await panel
      .getByRole('button', { name: 'Publishing guide revised', exact: true })
      .isVisible())
  )
    await panel
      .getByRole('button', { name: 'Back to articles', exact: true })
      .click();
  await panel
    .getByRole('button', { name: 'Publishing guide revised', exact: true })
    .waitFor();
  assert.deepEqual(errors, []);
  console.log(
    'Knowledge Base: catalog, section outline, reader/editor, local drafts, publishing, native history, attachment check-in and dependency deletion passed'
  );
} catch (error) {
  await page.screenshot({ path: output + '/failure.png' });
  await writeFile(output + '/failure.html', await page.content());
  throw error;
} finally {
  await browser.close();
}
