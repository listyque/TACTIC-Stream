import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.env.STREAM_REPORT_METRIC_CAPTURE;
if (output) await mkdir(output, { recursive: true });
const html = `<!doctype html><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue';
import Surface from '/src/features/objects/ObjectReportSurface.vue';
import {initializeAppearance,appearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
const width=ref(760),model={summary:{title:'Robot Arm',typeTitle:'Assets',code:'DEMO_ARM',searchType:'cg/assets',project:'CG Test',pipeline:'cg_test/assets',description:'Mechanical robot arm',searchKey:'cg/assets?code=DEMO_ARM'},metrics:{tasks:1,notes:2,children:5,participants:1,files:12,snapshots:6}};
Object.assign(appearance,{mode:'dark',language:'en',clickAnimations:false,hoverAnimations:false,fadeAnimations:false,popupAnimations:false});initializeAppearance();
window.metricHarness={width,appearance};
createApp({render:()=>h('main',{style:{width:width.value+'px',padding:'12px'}},h(Surface,{model}))}).mount('#app');</script>`;
const server = await createServer({
  root,
  configFile: false,
  logLevel: 'error',
  plugins: [
    vue(),
    {
      name: 'metric-fixture',
      configureServer(server) {
        server.middlewares.use(async (request, response, next) => {
          if (request.url !== '/metrics') return next();
          try {
            response.setHeader('Content-Type', 'text/html');
            response.end(await server.transformIndexHtml(request.url, html));
          } catch (error) {
            next(error);
          }
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const page = await browser.newPage({
      viewport: { width: 1800, height: 1000 }
    }),
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'metrics');
  await page.locator('[data-frame="objectReportMetric_7"]').waitFor();
  await page.evaluate(() => document.fonts.ready);
  for (const mode of ['dark', 'light'])
    for (const language of ['en', 'ru'])
      for (const width of [320, 560, 760, 1040, 1600]) {
        await page.evaluate(
          ({ mode, language, width }) => {
            Object.assign(window.metricHarness.appearance, { mode, language });
            window.metricHarness.width.value = width;
          },
          { mode, language, width }
        );
        await page.evaluate(
          () =>
            new Promise((resolve) =>
              requestAnimationFrame(() => requestAnimationFrame(resolve))
            )
        );
        const metrics = await page
          .locator('.frame-box[data-frame^="objectReportMetric_"]')
          .evaluateAll((elements) =>
            elements.map((element) => ({
              id: element.dataset.frame,
              radius: getComputedStyle(element).borderRadius,
              width: element.getBoundingClientRect().width,
              bottom: element.getBoundingClientRect().bottom,
              parentBottom: element
                .closest('.object-report-surface')
                .getBoundingClientRect().bottom,
              text: element.textContent
            }))
          );
        assert.equal(metrics.length, 8);
        for (const metric of metrics) {
          assert.equal(
            metric.radius,
            '0px',
            `${mode}/${language}/${width}: ${metric.id} clips glyph corners`
          );
          assert(
            metric.width > 0 && metric.bottom <= metric.parentBottom + 0.5,
            JSON.stringify(metric)
          );
          assert(metric.text.trim());
        }
        assert(
          parseFloat(
            await page
              .locator('[data-frame="objectReportHeaderSurface"]')
              .evaluate((element) => getComputedStyle(element).borderRadius)
          ) > 0,
          'Outer card keeps its rounded corners'
        );
        if (output && width === 760 && language === 'en')
          await page
            .locator('.object-report-surface')
            .screenshot({ path: output + '/browser-' + mode + '.png' });
      }
  assert.deepEqual(errors, []);
  console.log(
    'PASS: all eight statistic containers avoid rounded clipping; five widths, EN/RU, dark/light; outer card corners retained'
  );
} finally {
  await browser?.close();
  await server.close();
}
