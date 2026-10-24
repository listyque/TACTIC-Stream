// Actual installed UI and server; the parent owns the disposable fixture.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { selectProject } from './project_selection.mjs';

const [address, fixtureFile, output] = process.argv.slice(2);
assert(address.startsWith('http://127.0.0.1:'));
assert(process.env.RECOVERY_TEST_PASSWORD);
const fixtures = JSON.parse(await fs.readFile(fixtureFile, 'utf8'));
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const checks = [];
try {
  for (const [role, login] of [
    ['admin', 'admin'],
    ['artist', fixtures.ordinary_login]
  ]) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 }
    });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    const errors = [];
    const denied = [];
    const badRequests = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('response', (response) => {
      if (response.url().startsWith(address) && response.status() === 400)
        badRequests.push({
          path: new URL(response.url()).pathname,
          project: response.request().postDataJSON()?.project,
          body: response.text()
        });
      if (response.url().startsWith(address) && response.status() === 403)
        denied.push(new URL(response.url()).pathname);
      if (response.url().startsWith(address) && response.status() >= 500)
        errors.push(response.status() + ' ' + new URL(response.url()).pathname);
    });
    try {
      await page.addInitScript(() =>
        localStorage.setItem(
          'tactic_stream.appearance',
          JSON.stringify({ mode: 'dark', language: 'en' })
        )
      );
      await page.goto(address + '/');
      await page.getByLabel('Login', { exact: true }).fill(login);
      await page
        .getByLabel('Password', { exact: true })
        .fill(process.env.RECOVERY_TEST_PASSWORD);
      await page.getByRole('button', { name: 'Sign in', exact: true }).click();
      await page.locator('.project-picker').waitFor();
      for (const kind of ['vfx', 'game']) {
        const project = fixtures.templates[kind].project;
        assert(project.startsWith('l12_'));
        await selectProject(page, project);
        const entry = page
          .locator('.navigation-tree [data-search-type="' + kind + '/asset"]')
          .first();
        if (!(await entry.isVisible()))
          await page.locator('.navigation-toggle').click();
        await entry.click();
        await page
          .getByText('Artist update', { exact: true })
          .filter({ visible: true })
          .first()
          .waitFor();
        await page.screenshot({
          path: path.join(output, role + '-' + kind + '.png'),
          animations: 'disabled'
        });
        checks.push({ role, template: kind, project, asset_visible: true });
        if (kind === 'vfx') {
          const sequences = page
            .locator('.navigation-tree [data-search-type="vfx/sequence"]')
            .first();
          if (!(await sequences.isVisible()))
            await page.locator('.navigation-toggle').click();
          await sequences.click();
          const sequence = page
            .locator('.result-item-object')
            .filter({ hasText: 'L12_SEQ' })
            .first();
          await sequence.locator('.result-expand').click();
          const shots = page
            .locator('.result-item-branch')
            .filter({ hasText: 'Shot' })
            .first();
          await shots.locator('.result-expand').click();
          await page
            .locator('.result-item-object')
            .filter({ hasText: 'L12_SHOT' })
            .first()
            .waitFor();
          const references = page
            .locator('.result-item-branch')
            .filter({ hasText: 'Reference Images' })
            .first();
          await references.locator('.result-expand').click();
          await page
            .getByText('L12_REFERENCE', { exact: true })
            .first()
            .waitFor();
          await page.screenshot({
            path: path.join(output, role + '-vfx-sequence-tree.png'),
            animations: 'disabled'
          });
          checks.push({
            role,
            template: kind,
            project,
            sequence_shots_tree: true
          });
          await page
            .getByLabel('Change search results view', { exact: true })
            .click();
          await page
            .getByRole('menuitemradio', { name: 'Table', exact: true })
            .click();
          const table = page
            .locator('.handler-table')
            .filter({ visible: true })
            .first();
          await table.getByText('L12_SEQ', { exact: true }).waitFor();
          await table
            .getByRole('button', { name: 'Show related table', exact: true })
            .first()
            .click();
          const nested = page
            .locator('.nested-table')
            .filter({ visible: true })
            .first();
          await nested.getByText('L12_SHOT', { exact: true }).waitFor();
          await nested
            .getByText('1001 - 1100 (993 - 1108)', { exact: true })
            .waitFor();
          assert.equal(
            await page.getByText('Widget unavailable', { exact: true }).count(),
            0
          );
          assert.equal(
            await page.locator('.error-text').filter({ visible: true }).count(),
            0
          );
          await page.screenshot({
            path: path.join(output, role + '-vfx-sequence-table.png'),
            animations: 'disabled'
          });
          checks.push({
            role,
            template: kind,
            project,
            sequence_shots_table: true
          });
        }
      }
      await page.locator('.settings-menu > summary').click();
      const administration = page
        .locator('.settings-menu')
        .getByRole('button', { name: 'Administration', exact: true });
      assert.equal(await administration.isVisible(), role === 'admin');
      assert.deepEqual(errors, []);
      await fs.writeFile(
        path.join(output, role + '-bad-requests.json'),
        JSON.stringify(
          await Promise.all(
            badRequests.map(async ({ path, project, body }) => ({
              path,
              project,
              body: await body
            }))
          ),
          null,
          2
        )
      );
      assert.deepEqual(badRequests, [], 'Installed UI returned HTTP 400');
    } catch (error) {
      await fs.writeFile(
        path.join(output, role + '-denied.json'),
        JSON.stringify(denied, null, 2)
      );
      await page.screenshot({
        path: path.join(output, role + '-failure.png'),
        animations: 'disabled'
      });
      await fs.writeFile(
        path.join(output, role + '-body.txt'),
        await page.locator('body').innerText()
      );
      throw error;
    } finally {
      await context.close();
    }
  }
  const report = {
    status: 'passed',
    checks,
    real_login_and_navigation: true,
    administrator_menu_scoped: true
  };
  await fs.writeFile(
    path.join(output, 'result.json'),
    JSON.stringify(report, null, 2) + '\n'
  );
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
}
