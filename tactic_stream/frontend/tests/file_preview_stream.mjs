import assert from 'node:assert/strict';
import { fileBlob, previewFile } from '../src/features/objects/previewFiles.js';

let bytes = 0,
  cancelled = false;
const text = new ReadableStream({
  pull(controller) {
    const chunk = new Uint8Array(16384).fill(65);
    bytes += chunk.byteLength;
    controller.enqueue(chunk);
  },
  cancel() {
    cancelled = true;
  }
});
const preview = await previewFile(
  { filename: 'large.txt' },
  async () => new Response(text, { headers: { 'Content-Type': 'text/plain' } })
);
assert.equal(preview.text.length, 100000);
assert.equal(preview.truncated, true);
assert.equal(cancelled, true);
assert.ok(bytes < 140000, `Read ${bytes} bytes from large text`);
assert.deepEqual(
  await previewFile(
    { filename: 'small.txt' },
    async () => new Blob(['Короткий текст'], { type: 'text/plain' })
  ),
  { type: 'text/plain', text: 'Короткий текст' }
);

globalThis.location = { href: 'http://localhost/projects/one/' };
globalThis.document = {
  createElement: () => ({ canPlayType: () => 'probably' })
};
assert.deepEqual(
  await previewFile({ filename: 'clip.mp4', href: '/assets/clip.mp4' }, () => {
    assert.fail('Repository media must load through the native player');
  }),
  { type: 'video/mp4', url: 'http://localhost/assets/clip.mp4' }
);

const abort = new AbortController();
globalThis.fetch = (_url, { signal }) =>
  new Promise((_, reject) => {
    assert.equal(signal, abort.signal);
    signal.addEventListener('abort', () => reject(signal.reason));
  });
const stale = previewFile(
  { filename: 'text.txt', href: '/assets/text.txt' },
  fileBlob,
  abort.signal
);
abort.abort();
await assert.rejects(stale, { name: 'AbortError' });
