import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mkdir } from 'node:fs/promises';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = root + '../tools/frame_table/output/inline-editor/';
await mkdir(output, { recursive: true });
const html = `<html><body><div id="app"></div><script type="module">
import {createApp,h,nextTick} from 'vue';
import Editor from '/src/features/interface/TableInlineEditor.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css';import '/src/style.css';
Object.assign(appearance,{theme:'md3',mode:'dark',language:'en',clickAnimations:false,popupAnimations:false});initializeAppearance();
createApp({data(){return {editor:null,error:'',saved:[],cancelled:0}},mounted(){window.host=this},
 methods:{async open(mode,value){this.error='';this.editor={plans:[{}],field:{name:mode==='text'?'name':mode==='tags'?'keywords':'description',title:'Description',class_name:mode==='multiline'?'pyasm.widget.input_wdg.TextAreaWdg':'pyasm.widget.input_wdg.TextWdg',values:[value]}};await nextTick();await this.$refs.editor.open({left:20,top:60,bottom:96,width:280,height:36})}},
 render(){return h(Editor,{ref:'editor',editor:this.editor,error:this.error,onSave:value=>{this.saved.push(value);this.$refs.editor.close()},onCancel:()=>{this.cancelled++;this.$refs.editor.close()}})}}).mount('#app');
</script></body></html>`;
const server = await createServer({
  root,
  configFile: false,
  plugins: [
    vue(),
    {
      name: 'inline-editor-fixture',
      configureServer(server) {
        server.middlewares.use(async (request, response, next) => {
          if (request.url !== '/inline-editor-fixture') return next();
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
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, watch: null }
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
});
try {
  const page = await browser.newPage({
    viewport: { width: 1100, height: 700 }
  });
  page.setDefaultTimeout(6000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(server.resolvedUrls.local[0] + 'inline-editor-fixture');
  await page.waitForFunction(() => !!window.host);
  const popup = page.locator('.table-inline-editor:popover-open');
  const text =
    'Механическая рука робота.\nhttps://example.test/' +
    'reference_'.repeat(120);
  async function open(mode, value) {
    await page.evaluate(({ mode, value }) => window.host.open(mode, value), {
      mode,
      value
    });
    await popup.waitFor();
  }
  async function checkBounds() {
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    const geometry = await popup.evaluate((element) => {
      const outer = element.getBoundingClientRect();
      const boxes = [
        ...element.querySelectorAll(
          '[data-frame="tableInlineValue"], [data-frame="tableInlineSave"], [data-frame="tableInlineCancel"]'
        )
      ].map((child) => {
        const box = child.getBoundingClientRect();
        return { id: child.dataset.frame, left: box.left, right: box.right };
      });
      return {
        left: outer.left,
        right: outer.right,
        width: outer.width,
        height: outer.height,
        client: element.clientWidth,
        scroll: element.scrollWidth,
        viewport: innerWidth,
        boxes
      };
    });
    assert.ok(geometry.scroll <= geometry.client + 1, JSON.stringify(geometry));
    assert.ok(
      geometry.left >= 0 && geometry.right <= geometry.viewport,
      JSON.stringify(geometry)
    );
    for (const box of geometry.boxes)
      assert.ok(
        box.left >= geometry.left && box.right <= geometry.right,
        JSON.stringify({ geometry, box })
      );
    return geometry;
  }
  for (const viewport of [
    { width: 1100, height: 700 },
    { width: 320, height: 600 },
    { width: 800, height: 280 }
  ]) {
    await page.setViewportSize(viewport);
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))
        )
    );
    await open('multiline', text);
    const geometry = await checkBounds();
    await popup.screenshot({
      path: output + viewport.width + '-' + viewport.height + '.png'
    });
    if (viewport.width === 1100) {
      assert.equal(geometry.width, 620);
      assert.equal(geometry.height, 360);
    }
    await popup.getByRole('textbox').press('Enter');
    assert.equal(await popup.count(), 1, 'Enter keeps multiline editing open');
    await popup.getByRole('button', { name: 'Cancel', exact: true }).click();
    assert.equal(await page.evaluate(() => window.host.saved.length), 0);
  }
  await page.setViewportSize({ width: 1000, height: 700 });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))
      )
  );
  await open('multiline', text);
  await popup.getByRole('textbox').fill(text + '\nПроверено');
  await popup.getByRole('button', { name: 'Save', exact: true }).click();
  assert.deepEqual(await page.evaluate(() => window.host.saved), [
    text + '\nПроверено'
  ]);
  const tagNames = [
    'robot',
    'arm',
    'manipulator',
    'mechanical',
    'prop',
    'робот',
    'рука',
    'манипулятор',
    'WWWWWW'
  ];
  await open('tags', tagNames.join(', '));
  await checkBounds();
  for (const tag of tagNames) {
    const paint = await popup
      .getByRole('button', { name: tag, exact: true })
      .evaluate((button) => {
        const label = button.querySelector(
          ':scope > span:not(.app-icon):not(.control-ripple-clip):not(.app-button-badge)'
        );
        const text = document.createRange();
        text.selectNodeContents(label);
        return {
          available: label.clientWidth,
          text: text.getBoundingClientRect().width
        };
      });
    assert.ok(
      paint.text <= paint.available + 1,
      tag + ': ' + JSON.stringify(paint)
    );
  }
  await popup.screenshot({ path: output + 'tags.png' });
  await popup.press('Escape');
  await open(
    'tags',
    Array.from({ length: 60 }, (_, i) => 'tag_' + i).join(', ')
  );
  await checkBounds();
  await popup.press('Escape');
  await open('text', 'Robot');
  await page.evaluate(
    () => (window.host.error = 'A validation error keeps the editor available.')
  );
  await checkBounds();
  await popup.press('Escape');
  assert.deepEqual(errors, []);
  console.log(
    'Inline editor: wide/narrow/short bounds, long URLs, tags, errors, multiline Enter, Cancel and Save passed'
  );
} finally {
  await browser.close();
  await server.close();
}
