import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('..', import.meta.url)),
  output = fileURLToPath(
    new URL('../../.screenshots/gantt-scroll/', import.meta.url)
  );
const fixture = JSON.parse(
  await readFile(
    new URL('./task_schedule_fixture.json', import.meta.url),
    'utf8'
  )
);
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h,reactive} from 'vue'
import TaskGanttView from '/src/features/tasks/TaskGanttView.vue'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{mode:'dark',language:'ru',popupAnimations:false});initializeAppearance()
window.fixture=${JSON.stringify(fixture.gantt)}
window.state=reactive({width:871.25,height:872.75,gantt:{...window.fixture,records:[]}})
createApp({setup(){return ()=>h('div',{style:{width:state.width+'px',height:state.height+'px'}},[
 h(TaskGanttView,{projection:{gantt:state.gantt}})
])}}).mount('#app')
</script></body></html>`;
let server, browser;
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'scroll-fixture',
        configureServer(instance) {
          instance.middlewares.use('/scroll-test', async (req, res, next) => {
            try {
              res.setHeader('Content-Type', 'text/html');
              res.end(await instance.transformIndexHtml(req.url, html));
            } catch (error) {
              next(error);
            }
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0 }
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    ignoreDefaultArgs: ['--hide-scrollbars']
  });
  for (const deviceScaleFactor of [1, 1.25, 1.5]) {
    const page = await browser.newPage({
      viewport: { width: 1200, height: 1000 },
      deviceScaleFactor
    });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(
      'http://127.0.0.1:' + server.httpServer.address().port + '/scroll-test'
    );
    await page.locator('.gantt-body').waitFor();
    await page.evaluate(() => document.fonts.ready);
    for (const mode of ['empty', 'rows', 'overflow'])
      for (const [width, height] of [
        [871.25, 872.75],
        [1091.6, 691.4]
      ]) {
        const empty = mode === 'empty';
        await page.evaluate(
          ({ mode, width, height }) =>
            Object.assign(window.state, {
              width,
              height,
              gantt:
                mode === 'empty'
                  ? {
                      ...window.fixture,
                      days: 1,
                      records: [],
                      tickSets: {},
                      weekends: [],
                      milestones: [],
                      overview: [],
                      todayDay: -1,
                      scheduled: 0,
                      unscheduled: 0,
                      rangeStart: '',
                      rangeEnd: '',
                      warnings: 0
                    }
                  : mode === 'rows'
                    ? window.fixture
                    : {
                        ...window.fixture,
                        records: Array.from({ length: 40 }, (_, index) => ({
                          ...window.fixture.records[0],
                          taskCode: 'scroll-' + index,
                          ganttSectionFirst: index === 0,
                          groupFirst: false
                        }))
                      }
            }),
          { mode, width, height }
        );
        const samples = await page.evaluate(async () => {
          const values = [];
          let area;
          const observer = new ResizeObserver(
            (entries) => (area = entries[0].contentRect)
          );
          observer.observe(document.querySelector('.gantt-body'));
          for (let i = 0; i < 110; i++) {
            await new Promise(requestAnimationFrame);
            const body = document.querySelector('.gantt-body'),
              canvas = document.querySelector('.gantt-canvas');
            if (i >= 50)
              values.push([
                body.clientWidth,
                body.clientHeight,
                body.scrollWidth,
                body.scrollHeight,
                canvas.style.width,
                canvas.style.height,
                area.width,
                area.height
              ]);
          }
          observer.disconnect();
          return values;
        });
        const unique = [...new Set(samples.map(JSON.stringify))];
        console.log({ deviceScaleFactor, mode, width, height, unique });
        await page.screenshot({
          path: output + `/stream-${deviceScaleFactor}-${mode}-${width}.png`
        });
        assert.equal(
          unique.length,
          1,
          'Gantt scroll geometry must stop changing while idle'
        );
        if (empty)
          assert.ok(
            parseFloat(samples[0][4]) <= samples[0][6] + 0.02 &&
              parseFloat(samples[0][5]) <= samples[0][7] + 0.02,
            'An empty fitting timeline must not overflow, including fractional pixels'
          );
        if (mode === 'overflow') {
          assert.ok(samples[0][3] > samples[0][1]);
          await page
            .locator('.gantt-body')
            .hover({ position: { x: 80, y: 100 } });
          await page.mouse.wheel(0, 350);
          await page.waitForFunction(
            () => document.querySelector('.gantt-body').scrollTop > 0
          );
        }
      }
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log(
    'PASS: empty/populated Gantt remains stable at fractional sizes and 100/125/150% scale'
  );
} finally {
  await browser?.close();
  await server?.close();
}
