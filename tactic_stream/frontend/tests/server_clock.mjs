import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mock } from 'node:test';
import { computed, shallowReactive } from 'vue';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
import { ServerClock, serverTimestamp } from '../src/serverClock.js';

const epoch = Date.parse('2026-10-28T00:30:00Z');
let mono = 1000;
const timer = mock.method(performance, 'now', () => mono);
const wall = mock.method(Date, 'now', () => epoch + 9 * 3600000);
const clock = new ServerClock();
const sample = {
  utcStarted: new Date(epoch + 50).toISOString(),
  utcEnded: new Date(epoch + 150).toISOString()
};
assert(clock.observe(sample, 800, 1000));
assert.equal(clock.now(), epoch + 200);
mono += 90000;
assert.equal(clock.now(), epoch + 90200);
assert.equal(serverTimestamp('2026-10-28 00:30:00').getTime(), epoch);
assert.equal(serverTimestamp('2026-10-28T03:30:00+03:00').getTime(), epoch);
assert(!clock.observe(sample, 0, 900)); // Out of order.
assert(!clock.observe(sample, 0, NaN));
assert(!clock.observe(sample, 1000, 900));
assert(!clock.observe(sample, 1000, 1100 - 20)); // Impossible negative network delay.
assert(!clock.observe(sample, 1000, 10000)); // Slow sample cannot replace a good one.
assert.equal(clock.now(), epoch + 90200);
const reactiveClock = shallowReactive(clock);
let evaluations = 0;
const label = computed(() => {
  evaluations++;
  return reactiveClock.now();
});
label.value;
assert(
  reactiveClock.observe(
    {
      utcStarted: new Date(epoch + 250).toISOString(),
      utcEnded: new Date(epoch + 350).toISOString()
    },
    1000,
    1200
  )
);
label.value;
assert.equal(
  evaluations,
  1,
  'Routine samples invalidated all timestamp consumers'
);
assert(
  !reactiveClock.observe(
    { utcStarted: '2026-10-28T00:30:00', utcEnded: '2026-10-28T00:30:00' },
    1200,
    1400
  )
);
reactiveClock.observe(
  {
    utcStarted: new Date(epoch + 2250).toISOString(),
    utcEnded: new Date(epoch + 2350).toISOString()
  },
  1200,
  1400
);
label.value;
assert.equal(
  evaluations,
  2,
  'A significant server correction did not refresh timestamps'
);
timer.mock.restore();
wall.mock.restore();

const root = fileURLToPath(new URL('..', import.meta.url));
const html = `<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h,ref} from 'vue';
import {activityFeed} from '/src/api.js';
import {serverEventStream} from '/src/features/connection/serverEventStream.js';
import {serverClock,serverTimestamp} from '/src/serverClock.js';
import {timestampLabel,timestampFullLabel,dateKey,dayLabel} from '/src/features/activity/activity.js';
import ActivityEventCard from '/src/features/activity/ActivityEventCard.vue';
import {appearance,initializeAppearance} from '/src/appearance.js';
import '/src/theme.css'; import '/src/style.css';
Object.assign(appearance,{language:'en',mode:'dark'});initializeAppearance();
const rows=ref([]);
createApp({render(){return h(ActivityEventCard,{record:rows.value[0] || {}})}}).mount('#app');
window.load=async()=>{const result=await activityFeed('fixture','one');rows.value=result.records;return {
pretty:timestampLabel(result.records[0].timestamp), full:timestampFullLabel(result.records[0].timestamp),
day:dateKey(serverTimestamp(result.records[0].timestamp)), today:dayLabel(dateKey(serverTimestamp(result.records[0].timestamp))),
now:serverClock.now()}};
window.clock=serverClock;
window.streamClock=async()=>{
 serverClock.anchor.utc=null;let delivered=false;const controller=new AbortController();
 await serverEventStream('/admin/server-events',{},()=>{delivered=true;controller.abort();},controller.signal)
  .catch(error=>{if(!delivered)throw error;});
 return serverClock.now();
};
</script></body></html>`;
const server = await createServer({
  root,
  configFile: false,
  cacheDir: root + '/node_modules/.vite/server-clock',
  plugins: [
    vue(),
    {
      name: 'clock-fixture',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (req.url === '/') {
            res.setHeader('Content-Type', 'text/html');
            res.end(await server.transformIndexHtml(req.url, html));
            return;
          }
          if (req.url === '/admin/server-events') {
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader(
              'X-Tactic-UTC-Started',
              new Date(epoch).toISOString()
            );
            res.setHeader('X-Tactic-UTC-Ended', new Date(epoch).toISOString());
            res.end('event: updates\ndata: {}\n\n');
            return;
          }
          if (req.url === '/admin/activity-feed') {
            let body = '';
            req.on('data', (chunk) => (body += chunk));
            req.on('end', () => {
              assert(
                [
                  'UTC',
                  'Europe/Moscow',
                  'America/Los_Angeles',
                  'Pacific/Auckland'
                ].includes(JSON.parse(body).time_zone)
              );
              res.setHeader('Content-Type', 'application/json');
              res.setHeader(
                'X-Tactic-UTC-Started',
                new Date(epoch).toISOString()
              );
              res.setHeader(
                'X-Tactic-UTC-Ended',
                new Date(epoch).toISOString()
              );
              res.end(
                JSON.stringify({
                  result: {
                    records: [
                      {
                        eventId: 'change:1',
                        kind: 'change',
                        timestamp: '2026-10-28 00:30:00',
                        actor: 'admin',
                        actorLabel: 'Admin',
                        targetTitle: 'Clock test',
                        targetType: 'contract/entity',
                        title: 'Updated item'
                      }
                    ]
                  }
                })
              );
            });
            return;
          }
          next();
        });
      }
    }
  ],
  server: { host: '127.0.0.1', port: 0 }
});
await server.listen();
const browser = await chromium.launch({ headless: true });
try {
  for (const [timezoneId, day, hour] of [
    ['UTC', '2026-10-28', '00:30:00'],
    ['Europe/Moscow', '2026-10-28', '03:30:00'],
    ['America/Los_Angeles', '2026-10-27', '17:30:00'],
    ['Pacific/Auckland', '2026-10-28', '13:30:00']
  ]) {
    const context = await browser.newContext({
      timezoneId,
      viewport: { width: 800, height: 400 }
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.addInitScript(() => {
      Date.now = () => 0;
    });
    await page.goto(server.resolvedUrls.local[0]);
    await page
      .waitForFunction(() => window.load)
      .catch((error) => {
        throw new Error(errors.join('\n') || error.message);
      });
    const labels = await page.evaluate(() => window.load());
    assert.equal(labels.pretty, 'Just now', timezoneId);
    assert(labels.full.includes(hour), JSON.stringify(labels));
    assert.equal(labels.day, day);
    assert(labels.today.startsWith('Today'), JSON.stringify(labels));
    assert(Math.abs(labels.now - epoch) < 2000);
    await page.getByText('Just now', { exact: true }).waitFor();
    const before = await page.evaluate(() => window.clock.now());
    await page.evaluate(() => {
      Date.now = () => 9999999999999;
    });
    const after = await page.evaluate(() => window.clock.now());
    assert(
      after >= before && after - before < 2000,
      'Wall-clock jump changed server UTC'
    );
    const streamed = await page.evaluate(() => window.streamClock());
    assert(
      Math.abs(streamed - epoch) < 2000,
      'SSE handshake did not synchronize'
    );
    assert.deepEqual(errors, []);
    await context.close();
  }
  console.log(
    'Server clock: monotonic UTC, API transport, four browser time zones and real event cards passed.'
  );
} finally {
  await browser.close();
  await server.close();
}
