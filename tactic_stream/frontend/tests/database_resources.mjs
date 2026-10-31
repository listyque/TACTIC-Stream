import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.env.DATABASE_RESOURCE_CAPTURE;
if (output) await mkdir(output, { recursive: true });
const fixture = () => ({
  identity: 'external',
  revision: 'one',
  canWrite: true,
  document: {
    code: 'external',
    vendor: 'PostgreSQL',
    host: 'database.example',
    port: '5432',
    login: 'studio',
    password: '',
    clearPassword: false
  },
  catalog: [
    { identity: 'external', title: 'external' },
    { identity: 'new', title: 'New resource' }
  ],
  metadata: {
    hasPassword: true,
    notice: '',
    projects: [
      {
        code: 'demo',
        title: 'Demo project',
        database: 'demo_db',
        resource: 'external',
        retired: false
      }
    ]
  }
});
const html = `<!doctype html><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue';
import Resources from '/src/features/configuration/DatabaseResources.vue';
import Configuration from '/src/features/configuration/Configuration.vue';
import {windowDirective} from '/src/controls/window.js';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
const editor=ref(null),allowed=ref(true),width=ref(784);window.resourceFixture={editor,allowed,appearance,width};
const full=location.pathname==='/configuration-fixture';if(full)localStorage.setItem('tactic_stream.configuration.page','database_resources');
createApp({render:()=>full?h(Configuration,{ref:editor,ticket:'fixture',project:'demo',login:'admin',canAdminister:allowed.value,style:{width:'1000px',height:'900px'}}):h(Resources,{ref:editor,ticket:'fixture',active:true,canAdminister:allowed.value,style:{width:width.value+'px',height:'824px'}})}).directive('window',windowDirective).mount('#app');
</script>`;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  plugins: [
    vue(),
    {
      name: 'resources-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (
            !['/resources-fixture', '/configuration-fixture'].includes(req.url)
          )
            return next();
          res.setHeader('Content-Type', 'text/html');
          res.end(await server.transformIndexHtml(req.url, html));
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
let browser;
try {
  browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const page = await browser.newPage({
    viewport: { width: 1000, height: 900 },
    hasTouch: true
  });
  page.setDefaultTimeout(8000);
  const errors = [],
    writes = [];
  page.on('pageerror', (error) => errors.push(error.message));
  let saved = fixture();
  await page.route('**/admin/configuration', (route) =>
    route.fulfill({
      json: {
        result: {
          revision: 'one',
          groups: [],
          undocumented: [],
          runtime: { available: false }
        }
      }
    })
  );
  await page.route(
    '**/admin/configuration/database-resources/*',
    async (route) => {
      const action = route.request().url().split('/').at(-1),
        payload = route.request().postDataJSON();
      writes.push({ action, payload });
      if (action === 'save')
        saved = {
          ...saved,
          revision: 'two',
          document: { ...payload.document, password: '' }
        };
      const result = structuredClone(saved);
      if (action === 'test')
        result.metadata.notice = 'Database connection succeeded';
      if (action === 'upgrade')
        result.metadata.notice = 'Database schema is already current';
      await route.fulfill({ json: { result } });
    }
  );
  await page.goto(server.resolvedUrls.local[0] + 'resources-fixture');
  await page.locator('[data-frame="resourceField_host"]').waitFor();
  if (output)
    for (const [language, mode] of [
      ['en', 'dark'],
      ['ru', 'light']
    ]) {
      await page.evaluate(
        ({ language, mode }) =>
          Object.assign(window.resourceFixture.appearance, { language, mode }),
        { language, mode }
      );
      await page.locator('.database-resources').screenshot({
        path: output + '/browser-' + language + '-' + mode + '.png'
      });
    }
  await page.evaluate(() =>
    Object.assign(window.resourceFixture.appearance, {
      language: 'en',
      mode: 'dark'
    })
  );
  await page.locator('[data-frame="resourceField_host"]').fill('new.database');
  await page
    .locator('[data-frame="resourceField_password"]')
    .fill('draft-private-value');
  assert(await page.evaluate(() => window.resourceFixture.editor.value.dirty));
  assert(await page.locator('[data-frame="resource_test"]').isDisabled());
  await page.locator('[data-frame="resource_save"]').click();
  assert.equal(writes.filter((row) => row.action === 'save').length, 0);
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.waitForFunction(
    () =>
      !window.resourceFixture.editor.value.busy &&
      !window.resourceFixture.editor.value.dirty
  );
  const write = writes.find((row) => row.action === 'save').payload;
  assert.equal(write.document.password, 'draft-private-value');
  assert.equal(write.confirmation, 'save');
  assert.equal(
    await page.locator('[data-frame="resourceField_password"]').inputValue(),
    ''
  );
  await page.locator('[data-frame="resourceDatabase"]').fill('demo_db');
  await page.locator('[data-frame="resource_test"]').click();
  await page
    .getByText('Database connection succeeded', { exact: true })
    .waitFor();
  await page.locator('[data-frame="resource_upgrade"]').click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page
    .getByText('Database schema is already current', { exact: true })
    .waitFor();
  assert.equal(
    writes.find((row) => row.action === 'upgrade').payload.database,
    'demo_db'
  );
  await page.evaluate(() => (window.resourceFixture.allowed.value = false));
  await page
    .getByText('Database resources require administrator access', {
      exact: true
    })
    .waitFor();
  assert.deepEqual(errors, []);
  await page.evaluate(() => (window.resourceFixture.allowed.value = true));
  await page.setViewportSize({ width: 360, height: 740 });
  await page.evaluate(() => (window.resourceFixture.width.value = 360));
  const bind = page.locator('[data-frame="resource_bind"]');
  await page.waitForFunction(() => {
    const box = document
      .querySelector('[data-frame="resource_bind"]')
      ?.getBoundingClientRect();
    return box && box.x >= 0 && box.right <= 360;
  });
  await bind.scrollIntoViewIfNeeded();
  const bounds = await bind.boundingBox();
  assert(
    bounds.x >= 0 && bounds.x + bounds.width <= 360,
    JSON.stringify({
      bounds,
      layout: await page.locator('.database-resources').evaluate((el) => ({
        width: el.getBoundingClientRect().width,
        style: el.style.cssText,
        scrollX: window.scrollX
      }))
    })
  );
  await bind.tap();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.setViewportSize({ width: 1000, height: 900 });
  await page.goto(server.resolvedUrls.local[0] + 'configuration-fixture');
  const field = page.locator('[data-frame="resourceField_host"]');
  await field.waitFor();
  await field.fill('configured.example');
  await page.locator('[data-frame="configurationClose"]').click();
  await page.locator('[data-frame="configurationConfirm_keep"]').click();
  assert(await page.evaluate(() => window.resourceFixture.editor.value.dirty));
  await page.locator('[data-frame="configurationSave"]').click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.waitForFunction(() => !window.resourceFixture.editor.value.dirty);
  await field.fill('cancelled.example');
  await page.locator('[data-frame="configurationSave"]').click();
  await page.getByRole('button', { name: 'Continue', exact: true }).waitFor();
  await page.evaluate(() => (window.resourceFixture.allowed.value = false));
  await page
    .getByText('Database resources require administrator access', {
      exact: true
    })
    .waitFor();
  assert(await page.locator('[data-frame="configurationClose"]').isEnabled());
  assert.deepEqual(errors, []);
  console.log(
    'PASS: browser resource edit, password masking/reset, dirty guards, confirmations, saved connection test/schema action, role revocation, EN/RU themes'
  );
} finally {
  await browser?.close();
  await server.close();
}
