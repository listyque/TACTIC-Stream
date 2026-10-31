import assert from 'node:assert/strict';
import { readClipboardImages } from '../src/controls/clipboard.js';

const reads = [];
const item = (types) => ({
  types,
  getType: async (type) => {
    reads.push(type);
    return new Blob(['image'], { type });
  }
});
Object.defineProperty(navigator, 'clipboard', {
  value: {
    read: async () => [
      item(['text/plain']),
      item(['image/jpeg', 'image/png']),
      item(['image/jpeg'])
    ]
  },
  configurable: true
});
const files = await readClipboardImages();
assert.deepEqual(
  reads,
  ['image/png', 'image/jpeg'],
  'Choose one rendition per clipboard item'
);
assert.deepEqual(
  files.map((file) => [file.name, file.type]),
  [
    ['clipboard.png', 'image/png'],
    ['clipboard-2.jpg', 'image/jpeg']
  ]
);
navigator.clipboard.read = async () => {
  throw new Error('Permission denied');
};
await assert.rejects(readClipboardImages, /Permission denied/);
for (const name of ['NotAllowedError', 'SecurityError']) {
  navigator.clipboard.read = async () => {
    throw new DOMException('Denied', name);
  };
  assert.equal(await readClipboardImages(), null);
}
navigator.clipboard.read = async () => [item(['text/plain'])];
await assert.rejects(
  readClipboardImages,
  /The clipboard does not contain an image/
);
Object.defineProperty(navigator, 'clipboard', {
  value: undefined,
  configurable: true
});
assert.equal(await readClipboardImages(), null);
Object.defineProperty(navigator, 'clipboard', {
  value: {},
  configurable: true
});
assert.equal(await readClipboardImages(), null);
console.log(
  'Clipboard: images, empty clipboard, HTTP, denied access and unexpected errors OK'
);
