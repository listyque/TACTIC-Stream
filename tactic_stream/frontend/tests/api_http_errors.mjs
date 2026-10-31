import assert from 'node:assert/strict';
import { serverConfiguration, requestActivity } from '../src/api.js';
import { resetNotifications } from '../src/features/activity/notifications.js';

const fetch = globalThis.fetch;
try {
  for (const body of ['', '<html>Not Found</html>', 'null', '[]']) {
    globalThis.fetch = async () => new Response(body, { status: 404, statusText: 'Not Found' });
    await assert.rejects(serverConfiguration('fixture-ticket'), (error) =>
      error.status === 404 && error.message === 'HTTP 404: Not Found');
    assert.equal(requestActivity.pending.length, 0);
  }
  globalThis.fetch = async () => Response.json({ error: 'Access denied', error_code: 'authentication_failed' }, { status: 403 });
  await assert.rejects(serverConfiguration('fixture-ticket'), (error) =>
    error.status === 403 && error.message === 'Access denied' && error.code === 'authentication_failed');
  globalThis.fetch = async () => new Response('<html>Invalid success</html>');
  await assert.rejects(serverConfiguration('fixture-ticket'), SyntaxError);
  assert.equal(requestActivity.pending.length, 0);
  console.log('PASS: HTTP status survives non-JSON errors; structured errors and activity cleanup remain intact');
} finally {
  globalThis.fetch = fetch;
  resetNotifications();
}
